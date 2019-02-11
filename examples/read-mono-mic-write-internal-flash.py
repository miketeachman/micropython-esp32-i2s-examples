#
# This file is part of the MicroPython ESP32 project
#
# The MIT License (MIT)
#
# Copyright (c) 2019 Michael Shi
#
# https://opensource.org/licenses/MIT

# This example reads audio samples from an I2S microphone and writes
# them to a WAV file stored on the internal ESP32 flash memory.
#
# Testing was done with an INMP441 Microphone
#
# Recording duration is configured using RECORD_TIME_IN_SECONDS
#
# Audio samples from the INMP441 device have up to 24 bit precision. Here we'll
# be using 16 bit precision at 16khz sampling for decent audio quality. You
# can configure the number of seconds to record for via `RECORD_TIME_IN_SECONDS`
#
# Configuring DMA_LEN helps make sure that when writing to flash, there's
# enough bytes written at once to flash. This is important as writing too few
# bytes to flash at a time can increase latency and therefore lead to dropped
# audio samples over time. Flash memory seems to be buffered at
# 4096 bytes per write and a DMA_LEN of 512 allows 1024 bytes at a time to be
# read from DMA (512 * 2 bytes/sample) and be buffered for flash writing.

from machine import I2S
from machine import Pin

SAMPLE_BLOCK_SIZE = 4096
BITS_PER_SAMPLE = 16
BYTES_PER_SAMPLE = BITS_PER_SAMPLE // 8
SAMPLES_PER_SECOND = 16000
RECORD_TIME_IN_SECONDS = 8
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
sdin_pin = Pin(12)

audio_out = I2S(I2S.NUM0, bck=bck_pin, ws=ws_pin, sdin=sdin_pin,
    standard=I2S.PHILIPS, mode=I2S.MASTER_RX,
    dataformat=I2S.B16,                                                         # Each sample will only take up 2bytes in DMA memory
    # NOTE: ONLY_RIGHT actually samples left channel.
    channelformat=I2S.ONLY_RIGHT,                                               # Only sample single left channel (mono mic)
    samplerate=SAMPLES_PER_SECOND,
    dmacount=16,
    dmalen=DMA_LEN
)

s = open('/mic_recording.wav','wb')
s.write(wav_header)

mic_samples = bytearray(SAMPLE_BLOCK_SIZE)

TOTAL_BYTES = RECORD_TIME_IN_SECONDS * SAMPLES_PER_SECOND * BYTES_PER_SAMPLE
bytes_written = 0

# Keep recording until enough samples are written
while bytes_written < TOTAL_BYTES:
    try:
        numread = 0
        numwrite = 0
        numread = audio_out.readinto(mic_samples, timeout = 0)
        # If there were samples available in DMA, persist to flash
        if numread > 0:
          numwrite = s.write(mic_samples[:numread])
          bytes_written += numwrite
    except KeyboardInterrupt:
        break

s.close()
audio_out.deinit()
print('Done %d bytes written to flash' % bytes_written)
