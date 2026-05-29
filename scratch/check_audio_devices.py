import pyaudiowpatch as pyaudio

def list_wasapi_devices():
    p = pyaudio.PyAudio()
    try:
        host_api = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        host_api_index = host_api.get('index')
        print(f"WASAPI Host API Index: {host_api_index}")
        
        print("\nWASAPI Devices:")
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if dev.get('hostApi') == host_api_index:
                is_loopback = dev.get('isLoopbackDevice', False)
                print(f"ID {i}: {dev.get('name')} (Loopback: {is_loopback}, In: {dev.get('maxInputChannels')}, Out: {dev.get('maxOutputChannels')})")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        p.terminate()

if __name__ == "__main__":
    list_wasapi_devices()
