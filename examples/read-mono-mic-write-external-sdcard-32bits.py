#
# This file is part of the MicroPython ESP32 project
#
# The MIT License (MIT)
#
# Copyright (c) 2019 Michael Shi
# Copyright (c) 2019 Mike Teachman
#
# https://opensource.org/licenses/MIT

# This example reads audio samples from an I2S microphone and writes 
# them to a WAV file stored on an external SDCard.
#
# Testing was done with a SPH0645LM4H Microphone (Adafruit I2S MEMS Microphone breakout board)
#
# Recording duration is configured using RECORD_TIME_IN_SECONDS
#
# Audio samples from the SPH0645LM4H device have up to 18 bit precision. Here we'll
# be using 32 bit precision at 16khz sampling for decent audio quality. You
# can configure the number of seconds to record for via `RECORD_TIME_IN_SECONDS`
#
# Configuring DMA_LEN helps make sure that when writing to flash, there's
# enough bytes written at once to flash. This is important as writing too few
# bytes to flash at a time can increase latency and therefore leads to dropped
# audio samples over time. Efficient writing of external SD memory is typically 
# achieved when the write buf is a multiple of the SD sector size (usually 512 bytes).
# Selecting a DMA_LEN of 512 allows 2048 bytes at a time to be
# read from DMA (512 * 4 bytes/sample) and be buffered for flash writing.

import uos
import sdcard
from machine import I2S
from machine import Pin
from machine import SPI

SAMPLE_BLOCK_SIZE = 8192
BITS_PER_SAMPLE = 32
BYTES_PER_SAMPLE = BITS_PER_SAMPLE // 8
SAMPLES_PER_SECOND = 16000
RECORD_TIME_IN_SECONDS = 10
DMA_LEN = 512

def gen_wav_header(sampleRate, bitsPerSample, num_channels, num_samples):
    datasize = num_samples * num_channels * bitsPerSample // 8
    o = bytes("RIFF",'ascii')                                                   # (4byte) Marks file as RIFF
    o += (datasize + 36).to_bytes(4,'little')                                   # (4byte) File size in bytes excluding this and RIFF marker
    o += bytes("WAVE",'ascii')                                                  # (4byte) File type
    o += bytes("fmt ",'ascii')                                                  # (4byte) Format Chunk Marker
    o += (16).to_bytes(4,'little')                                              # (4byte) Length of above format data
    o += (1).to_bytes(2,'little')                                               # (2byte) Format type (1 - PCM)
    o += (num_channels).to_bytes(2,'little')                                    # (2byte)
    o += (sampleRate).to_bytes(4,'little')                                      # (4byte)
    o += (sampleRate * num_channels * bitsPerSample // 8).to_bytes(4,'little')  # (4byte)
    o += (num_channels * bitsPerSample // 8).to_bytes(2,'little')               # (2byte)
    o += (bitsPerSample).to_bytes(2,'little')                                   # (2byte)
    o += bytes("data",'ascii')                                                  # (4byte) Data Chunk Marker
    o += (datasize).to_bytes(4,'little')                                        # (4byte) Data size in bytes
    return o

WAV_DATA_SIZE = RECORD_TIME_IN_SECONDS * SAMPLES_PER_SECOND * BYTES_PER_SAMPLE
wav_header = gen_wav_header(SAMPLES_PER_SECOND, BITS_PER_SAMPLE, 1, SAMPLES_PER_SECOND * RECORD_TIME_IN_SECONDS)

bck_pin = Pin(14)
ws_pin = Pin(13)
sdin_pin = Pin(27)

audio_in = I2S(I2S.NUM0, bck=bck_pin, ws=ws_pin, sdin=sdin_pin,
    standard=I2S.PHILIPS, mode=I2S.MASTER_RX,
    dataformat=I2S.B32,                                                         # Each sample will only take up 4bytes in DMA memory
    # NOTE: ONLY_RIGHT actually samples left channel.
    channelformat=I2S.ONLY_RIGHT,                                               # Only sample single left channel (mono mic)
    samplerate=SAMPLES_PER_SECOND,
    dmacount=32,
    dmalen=DMA_LEN
)

spi = SPI(1, sck=Pin(18), mosi=Pin(23), miso=Pin(19))
sd = sdcard.SDCard(spi, Pin(4))
uos.mount(sd, "/sd")
s = open('/sd/mic_recording_32bits.wav','wb')
s.write(wav_header)

mic_samples = bytearray(SAMPLE_BLOCK_SIZE)

TOTAL_BYTES = RECORD_TIME_IN_SECONDS * SAMPLES_PER_SECOND * BYTES_PER_SAMPLE
bytes_written = 0

# Keep recording until enough samples are written
while bytes_written < TOTAL_BYTES:
    try:
        numread = 0
        numwrite = 0
        numread = audio_in.readinto(mic_samples, timeout = 5)
        # If there were samples available in DMA, persist to flash
        if numread > 0:
          numwrite = s.write(mic_samples[:numread])
          bytes_written += numwrite
    except KeyboardInterrupt:
        break

s.close()
uos.umount("/sd")
spi.deinit()
audio_in.deinit()
print('Done %d bytes written to SD Card' % bytes_written)