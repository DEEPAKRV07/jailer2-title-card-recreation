# Probed input metadata

short
{'codec_type': 'video', 'codec_name': 'h264', 'width': 3840, 'height': 2160, 'r_frame_rate': '30/1', 'avg_frame_rate': '271000000/9033333', 'nb_frames': '271', 'duration': '9.033333', 'sample_rate': None, 'channels': None, 'time_base': '1/1000000'}
{'codec_type': 'audio', 'codec_name': 'aac', 'width': None, 'height': None, 'r_frame_rate': '0/0', 'avg_frame_rate': '0/0', 'nb_frames': '389', 'duration': '9.032562', 'sample_rate': '44100', 'channels': 2, 'time_base': '1/44100'}

extended
{'codec_type': 'video', 'codec_name': 'h264', 'width': 3840, 'height': 2160, 'r_frame_rate': '30/1', 'avg_frame_rate': '30/1', 'nb_frames': '654', 'duration': '21.800000', 'sample_rate': None, 'channels': None, 'time_base': '1/1000000'}
{'codec_type': 'audio', 'codec_name': 'aac', 'width': None, 'height': None, 'r_frame_rate': '0/0', 'avg_frame_rate': '0/0', 'nb_frames': '941', 'duration': '21.803991', 'sample_rate': '44100', 'channels': 2, 'time_base': '1/44100'}

Short-clip nominal frame rate: 30 fps; reported average 30.000001107011112 fps. The tiny difference is explained by the microsecond time base and rounded 9.033333-second duration for 271 frames, not a meaningful speed change. Extended nominal and average rates are both exactly 30/1.
Output is explicitly generated at constant 30 fps.