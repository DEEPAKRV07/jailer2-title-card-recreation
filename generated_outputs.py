"""Delete only inventoried generated artifacts whose content has not been replaced by a user."""
import hashlib,json
from pathlib import Path

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class GeneratedOutputs:
    def __init__(self,root,directory,kind):
        self.root=Path(root).resolve(); self.directory=(self.root/directory).resolve(); self.kind=kind
        # Destructive cleanup is allowed only in designated project previews/qa trees.
        expected=self.root/('previews' if kind=='preview' else 'qa')
        if not self.directory.is_relative_to(expected) or self.directory==self.root:
            raise ValueError(f'Automatic cleanup refused outside {expected}: {self.directory}')
        self.directory.mkdir(parents=True,exist_ok=True)
        self.manifest=self.directory/f'.generated_{kind}.json'
        self.entries={}
        if self.manifest.exists():
            data=json.loads(self.manifest.read_text())
            self.entries=data.get('files',{})
    def safe(self,relative):
        unresolved=self.directory/relative
        if unresolved.is_symlink():raise ValueError('Refusing to clean a symbolic link.')
        path=unresolved.resolve()
        if not path.is_relative_to(self.directory) or path==self.directory:
            raise ValueError('Unsafe generated-output manifest path; no cleanup performed.')
        if path.is_symlink(): raise ValueError('Refusing to clean a symbolic link.')
        return path
    def clean(self):
        # Preflight ALL paths before deleting any; altered user files are preserved.
        candidates=[(self.safe(name),sha) for name,sha in self.entries.items()]
        preserved=[]
        for path,sha in candidates:
            if path.is_file():
                if digest(path)==sha: path.unlink()
                else: preserved.append(path.name)
        self.entries={}; self.save()
        if preserved: print('Preserved files changed outside the generator: '+', '.join(preserved),flush=True)
    def register(self,path):
        path=Path(path).resolve()
        if not path.is_relative_to(self.directory): return
        self.entries[str(path.relative_to(self.directory))]=digest(path); self.save()
    def reserve(self,paths):
        for path in paths:
            path=Path(path).resolve()
            if not path.is_relative_to(self.directory):raise ValueError('Generated output would escape its designated directory.')
            if path.exists() and self.entries.get(str(path.relative_to(self.directory)))!=digest(path):raise ValueError(f'Preserving untracked file {path.name}. Move it out of {self.directory.name} before generating this output.')
    def save(self):
        self.manifest.write_text(json.dumps({'kind':self.kind,'files':self.entries},indent=2))

def migrate_known_outputs(root):
    """One-time explicit inventory from the inspected old project, never a wildcard deletion."""
    root=Path(root)
    inventory=root/'development/legacy_generated_inventory.json'
    if not inventory.exists(): return
    for kind,rows in json.loads(inventory.read_text()).items():
        tracker=GeneratedOutputs(root,'previews' if kind=='preview' else 'qa',kind)
        if tracker.manifest.exists(): continue
        for relative,sha in rows.items():
            path=tracker.safe(relative)
            if path.exists() and digest(path)==sha: tracker.entries[relative]=sha
        tracker.save()
