import PySpin
import numpy as np
import cv2
import gi
import time

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

MAX_RETRY = 5

def on_need_data(appsrc, length, camera):
    print("on_need_data called, attempting to retrieve image.")
    retry_count = 0
    while retry_count < MAX_RETRY:
        image = camera.GetNextImage()
        if image.IsIncomplete():
            print(f"Image incomplete: {image.GetImageStatus()}, retrying... ({retry_count+1}/{MAX_RETRY})")
            image.Release()
            retry_count += 1
            continue

        frame = image.GetNDArray()
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            frame_rgb = frame
        else:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BayerBG2RGB)

        frame_resized = cv2.resize(frame_rgb, (640, 480))
        data = frame_resized.tobytes()
        buf = Gst.Buffer.new_wrapped(data)
        appsrc.emit('push-buffer', buf)
        print("Image pushed to appsrc.")
        image.Release()
        break

    if retry_count == MAX_RETRY:
        print("Failed to get a complete image after retries.")

def configure_camera(camera):
    print("Configuring camera settings...")
    camera.BalanceWhiteAuto.SetValue(PySpin.BalanceWhiteAuto_Continuous)
    camera.GainAuto.SetValue(PySpin.GainAuto_Continuous)
    camera.ExposureAuto.SetValue(PySpin.ExposureAuto_Continuous)
    try:
        camera.GammaEnable.SetValue(True)
        camera.Gamma.SetValue(0.9)
        print("Gamma correction enabled.")
    except PySpin.SpinnakerException as e:
        print(f"Gamma correction not supported: {e}")

    camera.AcquisitionFrameRateEnable.SetValue(True)
    frame_rate = min(30.0, camera.AcquisitionFrameRate.GetMax())
    camera.AcquisitionFrameRate.SetValue(frame_rate)
    print(f"Frame rate set to {frame_rate}.")

def spinnaker_to_udp():
    print("Initializing Spinnaker system...")
    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    if cam_list.GetSize() == 0:
        print("No cameras detected.")
        system.ReleaseInstance()
        return

    print("Camera detected. Initializing...")
    camera = cam_list[0]
    camera.Init()
    configure_camera(camera)
    camera.BeginAcquisition()

    print("Initializing GStreamer pipeline...")
    Gst.init(None)
    pipeline = Gst.parse_launch(
    "appsrc name=source is-live=true block=true format=time "
    "caps=video/x-raw,format=RGB,width=640,height=480,framerate=30/1 ! "
    "videoconvert ! videobalance brightness=0.3 contrast=1.2 ! "
    "vp8enc keyframe-max-dist=1 deadline=1 target-bitrate=2000000 ! "
    "rtpvp8pay ! udpsink host=15.181.49.61 port=5000 sync=false"
)

    appsrc = pipeline.get_by_name("source")
    appsrc.connect("need-data", on_need_data, camera)

    print("Starting GStreamer pipeline...")
    pipeline.set_state(Gst.State.PLAYING)

    try:
        GLib.MainLoop().run()
    except KeyboardInterrupt:
        print("Streaming stopped by user.")
    finally:
        print("Stopping pipeline and releasing resources.")
        pipeline.set_state(Gst.State.NULL)
        camera.EndAcquisition()
        camera.DeInit()
        cam_list.Clear()
        system.ReleaseInstance()
        print("Resources released. Exiting.")

if __name__ == "__main__":
    spinnaker_to_udp()
