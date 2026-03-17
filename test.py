import os
import subprocess

def test_stretch():
    # 1. create dummy 10s video
    subprocess.run("ffmpeg -y -f lavfi -i testsrc=duration=10:size=640x480:rate=30 -c:v libx264 test_in.mp4", shell=True, check=True)
    
    # 2. define blocks
    blocks = [
        {"start": 0, "end": 4, "old": 4, "new": 4},
        {"start": 4, "end": 6, "old": 2, "new": 6},   # stretch 2s -> 6s
        {"start": 6, "end": 10, "old": 4, "new": 2}   # squeeze 4s -> 2s
    ]
    
    # 3. generate script
    filter_lines = []
    concat_inputs = []
    
    for i, b in enumerate(blocks):
        rate = b["new"] / b["old"]
        line = f"[0:v]trim=start={b['start']}:end={b['end']},setpts={rate}*(PTS-STARTPTS)[v{i}];"
        filter_lines.append(line)
        concat_inputs.append(f"[v{i}]")
        
    concat_line = "".join(concat_inputs) + f"concat=n={len(blocks)}:v=1:a=0[outv]"
    filter_lines.append(concat_line)
    
    script_path = "test_script.txt"
    with open(script_path, "w") as f:
        f.write("\n".join(filter_lines))
        
    # 4. run ffmpeg
    cmd = f"ffmpeg -y -i test_in.mp4 -filter_complex_script {script_path} -map \"[outv]\" -c:v libx264 test_out.mp4"
    subprocess.run(cmd, shell=True, check=True)
    
    # 5. verify duration
    res = subprocess.run("ffprobe -v error -show_entries format=duration -of default=noprintwrappers=1:nokey=1 test_out.mp4", shell=True, check=True, capture_output=True, text=True)
    print("New duration:", res.stdout.strip())

if __name__ == "__main__":
    test_stretch()
