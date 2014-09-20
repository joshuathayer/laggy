import pyaudio
import StringIO
import wave

SHORT_NORMALIZE = (1.0/32768.0)
chunk           = 1024
FORMAT          = pyaudio.paInt16
CHANNELS        = 1
RATE            = 16000
swidth          = 2
Max_Seconds     = 10
TimeoutSignal   = ((RATE / chunk * Max_Seconds) + 2)
silence         = True
FileNameTmp     = '/tmp/hello.wav'
Time            = 0

p = pyaudio.PyAudio()

class Rec():

    def __init__(self):
        self._rec_state = False
        self.stream = None
        self.screen = None
        self.peer   = None
        self.log    = None

    def is_recording(self):
        return self._rec_state

    def open_stream(self, cb):
        stream = p.open(format            = FORMAT,
                        channels          = CHANNELS,
                        rate              = RATE,
                        input             = True,
                        frames_per_buffer = chunk,
                        stream_callback   = cb)
        return stream

    def get_stream(self, chunk, caller_cb):
        if self.stream is None:
            def cb(in_data, frame_count, time_info, status):
                caller_cb(in_data)
                return in_data, pyaudio.paContinue

            self.stream = self.open_stream(cb)
        else:
            self.log.err("stream already open")

        self.stream.start_stream()
    
    def do_rec(self):
 
        def handle_recorded(data):
            self.wf.writeframes(data)
            
        self.get_stream(1024, handle_recorded)
        
    def toggle(self):
        self._rec_state = not self._rec_state
        if self._rec_state:
            df = StringIO.StringIO()
            wf = wave.open(df, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(RATE)
            self.wf = wf
            self.df = df

            self.sender.alert("recording.")

            self.do_rec()
        else:
            self.stream.close() # not sure why, but stop_stream hangs
            self.wf.close()
            self.df.seek(0)

            data = self.df.read()

            self.sender.alert("done recording.")
            self.sender.send(data)

            self.stream = None
            # self.frames = []
