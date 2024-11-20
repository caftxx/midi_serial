import os
import sys
import time
import serial
import struct
from tqdm import tqdm

class MidiSerial:
    def __init__(self, midi_file, channel_id = 0, port='COM4', baudrate=115200, timeout=0.5):
        self.serial = serial.Serial(port, baudrate, timeout=timeout)
        self.midi_file = midi_file
        self.channel_id = channel_id
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

        #    2   |   1   |   1        |      1       |   ...
        #  magic | seqid | channel_id | payload_size | payload
        magic = struct.pack('H', self.magic)
        seqid = struct.pack('B', self.seqid)
        channel_id = struct.pack('B', self.channel_id)
        payload_size = struct.pack('B', size)
        self.serial.write(magic + seqid + channel_id + payload_size + payload)

    def rx(self, size, timeout = 5):
        begin = time.time()
        ret = b''
        while len(ret) != size:
            if time.time() - begin > timeout:
                raise TimeoutError(f"rx timeout, costtime:{time.time() - begin}")
            byte = self.serial.read_until(expected=[], size=1)
            if not byte:
                continue
            ret += byte
        return ret

    def send(self):
        file_size = os.path.getsize(self.midi_file)
        ticks = (file_size + 31) // 32
        for _ in tqdm(range(ticks)):
            payload = self.midi_file_reader.read(32)
            if not payload:
                break

            self.tx(payload)

            # seqid
            seqid = int.from_bytes(self.rx(1, 666))
            if seqid != self.seqid:
                raise ValueError(f"invalid rx seqid, expected:{self.seqid}, actual:{seqid}")

def main():
    if len(sys.argv) < 2:
        print("Usage: <midi filepath> [play channel id, default 0]")
        sys.exit(1)

    midi = MidiSerial(sys.argv[1], 0 if len(sys.argv) == 2 else int(sys.argv[2]))
    midi.send()

if __name__ == '__main__':
    main()