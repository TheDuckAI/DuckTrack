import os
import subprocess
import time
from platform import system

import obsws_python as obs
import psutil


def is_obs_running() -> bool:
    try:
        for process in psutil.process_iter(attrs=["pid", "name"]):
            if "obs" in process.info["name"].lower():
                return True
        return False
    except Exception as e:
        raise Exception("Could not check if OBS is running already. Please check manually.")

def close_obs(obs_process: psutil.Process):
    if obs_process:
        obs_process.terminate()
        try:
            obs_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            obs_process.kill()

def find_obs() -> str:
    # just some guesses at where obs might be installed
    paths = {
        "Windows": [
            "C:\\Program Files\\obs-studio\\bin\\64bit\\obs64.exe",
            "C:\\Program Files (x86)\\obs-studio\\bin\\32bit\\obs32.exe"
        ],
        "Darwin": [
            "/Applications/OBS.app/Contents/MacOS/OBS",
            "/opt/homebrew/bin/obs"
        ],
        "Linux": [
            "/usr/bin/obs",
            "/usr/local/bin/obs"
        ]
    }

    for path in paths.get(system(), []):
        if os.path.exists(path):
            return path
    
    try:
        if system() == "Windows":
            obs_path = subprocess.check_output("where obs", shell=True).decode().strip()
        else:
            obs_path = subprocess.check_output("which obs", shell=True).decode().strip()

        if os.path.exists(obs_path):
            return obs_path
    except subprocess.CalledProcessError:
        pass

    return "obs"

def open_obs() -> psutil.Process:
    try:
        return subprocess.Popen([find_obs(), "--startreplaybuffer", "--minimize-to-tray"])
    except Exception as e:
        raise FileNotFoundError("Failed to find OBS, please open OBS manually.")

class OBSClient:
    def __init__(
        self, 
        recording_path: str, 
        metadata: dict, 
        fps=30, 
        output_width=1280, 
        output_height=720, 
    ):
        self.metadata = metadata
        
        self.req_client = obs.ReqClient()
        self.event_client = obs.EventClient()
        
        self.record_state_events = {}
        
        def on_record_state_changed(data):
            output_state = data.output_state
            print("record state changed:", output_state)
            if output_state not in self.record_state_events:
                self.record_state_events[output_state] = []
            self.record_state_events[output_state].append(time.perf_counter())
        
        self.event_client.callback.register(on_record_state_changed)

        self.old_profile = self.req_client.get_profile_list().current_profile_name

        if "computer_tracker" not in self.req_client.get_profile_list().profiles:
            self.req_client.create_profile("computer_tracker")
        else:
            self.req_client.set_current_profile("computer_tracker")
            self.req_client.create_profile("temp")
            self.req_client.remove_profile("temp")
            self.req_client.set_current_profile("computer_tracker")

        base_width = metadata["screen_width"]
        base_height = metadata["screen_height"]
        
        if metadata["system"] == "Darwin":
            # for retina displays
            base_width *= 2
            base_height *= 2
        
        scaled_width, scaled_height = _scale_resolution(base_width, base_height, output_width, output_height)
        
        self.req_client.set_profile_parameter("Video", "BaseCX", str(base_width))
        self.req_client.set_profile_parameter("Video", "BaseCY", str(base_height))
        self.req_client.set_profile_parameter("Video", "OutputCX", str(scaled_width))
        self.req_client.set_profile_parameter("Video", "OutputCY", str(scaled_height))
        self.req_client.set_profile_parameter("Video", "ScaleType", "lanczos")

        self.req_client.set_profile_parameter("AdvOut", "RescaleRes", f"{base_width}x{base_height}")
        self.req_client.set_profile_parameter("AdvOut", "RecRescaleRes", f"{base_width}x{base_height}")
        self.req_client.set_profile_parameter("AdvOut", "FFRescaleRes", f"{base_width}x{base_height}")

        self.req_client.set_profile_parameter("Video", "FPSCommon", str(fps))
        self.req_client.set_profile_parameter("Video", "FPSInt", str(fps))
        self.req_client.set_profile_parameter("Video", "FPSNum", str(fps))
        self.req_client.set_profile_parameter("Video", "FPSDen", "1")
        
        self.req_client.set_profile_parameter("SimpleOutput", "RecFormat2", "mp4")
        
        bitrate = int(_get_bitrate_mbps(scaled_width, scaled_height, fps=fps) * 1000 / 50) * 50
        self.req_client.set_profile_parameter("SimpleOutput", "VBitrate", str(bitrate))
        
        # do this in order to get pause & resume
        self.req_client.set_profile_parameter("SimpleOutput", "RecQuality", "Small")

        self.req_client.set_profile_parameter("SimpleOutput", "FilePath", recording_path)
    
        self.req_client.set_input_mute("Mic/Aux", muted=True)
            
    def start_recording(self):
        self.req_client.start_record()

    def stop_recording(self):
        self.req_client.stop_record()
        self.req_client.set_current_profile(self.old_profile) # restore old profile

    def pause_recording(self):
        self.req_client.pause_record()
    
    def resume_recording(self):
        self.req_client.resume_record()
   
def _get_bitrate_mbps(width: int, height: int, fps=30) -> float:
    resolutions = {
        (7680, 4320): {30: 120, 60: 180},
        (3840, 2160): {30: 40,  60: 60.5},
        (2160, 1440): {30: 16,  60: 24},
        (1920, 1080): {30: 8,   60: 12},
        (1280, 720):  {30: 5,   60: 7.5},
        (640, 480):   {30: 2.5, 60: 4},
        (480, 360):   {30: 1,   60: 1.5}
    }

    if (width, height) in resolutions:
        return resolutions[(width, height)].get(fps)
    else:
        area = width * height
        multiplier = 3.5982188179592543e-06 if fps == 30 else 5.396175171097084e-06
        constant = 2.418399836285939 if fps == 30 else 3.742780056500365
        return multiplier * area + constant

def _scale_resolution(
    base_width: int, 
    base_height: int, 
    target_width: int, 
    target_height: int
) -> tuple[int, int]:
    target_area = target_width * target_height
    aspect_ratio = base_width / base_height
    
    scaled_height = int((target_area / aspect_ratio) ** 0.5)
    scaled_width = int(aspect_ratio * scaled_height)
    
    return scaled_width, scaled_height