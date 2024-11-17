import sys
import time
import serial
import struct

class MidiSerial:
    def __init__(self, midi_file, port='COM4', baudrate=115200, timeout=0.5):
        self.serial = serial.Serial(port, baudrate, timeout=timeout)
        self.midi_file = midi_file
        self.midi_file_reader = open(midi_file, mode='rb')
        self.magic = 0xbeef
        self.seqid = 0

    def __del__(self):
        self.serial.close()
        self.midi_file_reader.close()
    
    def tx(self, payload):
        size = len(payload)
        if size > 256:
            raise ValueError(f"payload size:{size} exceed limit 256")
        self.seqid = (self.seqid + 1) & 0xff

        #    2   |   1   |      1       |   ...
        #  magic | seqid | payload_size | payload
        magic = struct.pack('H', self.magic)
        seqid = struct.pack('B', self.seqid)
        payload_size = struct.pack('B', size)
        self.serial.write(magic + seqid + payload_size + payload)

    def rx(self, size, timeout = 5):
        begin = time.time()
        ret = b''
        while len(ret) != size:
            if time.time() - begin > 5:
                raise TimeoutError(f"rx timeout, costtime:{time.time() - begin}")
            byte = self.serial.read_until(expected=[], size=1)
            if not byte:
                continue
            ret += byte
        return ret;

    def send(self):
        while 1:
            payload = self.midi_file_reader.read(32)
            if not payload:
                break

            print(f"send seqid:{self.seqid+1}, size:{len(payload)}")
            self.tx(payload)

            # seqid
            seqid = int.from_bytes(self.rx(1))
            if seqid != self.seqid:
                raise ValueError(f"invalid rx seqid, expected:{self.seqid}, actual:{seqid}")

def main():
    if len(sys.argv) < 2:
        print("need midi file to send")
        sys.exit(1)

    midi = MidiSerial(sys.argv[1])
    midi.send()

if __name__ == '__main__':
    main()