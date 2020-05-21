# The MIT License (MIT)
# Copyright (c) 2020 Mike Teachman
# https://opensource.org/licenses/MIT

# Purpose:
# - read 16-bit audio samples from a stereo formatted WAV file 
#   stored in the internal MicroPython filesystem
# - write audio samples to an I2S amplifier or DAC module 
#
# Sample WAV file in wav_files folder:
#   "side-to-side-8k-16bits-stereo.wav"
#
# Hardware tested:
# - PCM5102 stereo DAC module
#
# The WAV file will play continuously until a keyboard interrupt is detected or
# the ESP32 is reset
  
from machine import I2S
from machine import Pin

#======= USER CONFIGURATION =======
WAV_FILE = 'side-to-side-8k-16bits-stereo.wav'
SAMPLE_RATE_IN_HZ = 8000
#======= USER CONFIGURATION =======

bck_pin = Pin(33) 
ws_pin = Pin(25)  
sdout_pin = Pin(32)

# channelformat setting:
#     stereo WAV: channelformat=I2S.RIGHT_LEFT
audio_out = I2S(
    I2S.NUM1, 
    bck=bck_pin, ws=ws_pin, sdout=sdout_pin, 
    standard=I2S.PHILIPS, 
    mode=I2S.MASTER_TX,
    dataformat=I2S.B16, 
    channelformat=I2S.RIGHT_LEFT,
    samplerate=SAMPLE_RATE_IN_HZ,
    dmacount=10, dmalen=512)

wav = open(WAV_FILE,'rb')

# advance to first byte of Data section in WAV file
pos = wav.seek(44) 

# allocate sample arrays
#   memoryview used to reduce heap allocation in while loop
wav_samples = bytearray(2048)
wav_samples_mv = memoryview(wav_samples)

print('Starting')
# continuously read audio samples from the WAV file 
# and write them to an I2S DAC
while True:
    try:
        num_read = wav.readinto(wav_samples_mv)
        num_written = 0
        # end of WAV file?
        if num_read == 0:
            # advance to first byte of Data section
            pos = wav.seek(44) 
        else:
            # loop until all samples are written to the I2S peripheral
            while num_written < num_read:
                num_written += audio_out.write(wav_samples_mv[num_written:num_read], timeout=0)
    except (KeyboardInterrupt, Exception) as e:
        print('caught exception {} {}'.format(type(e).__name__, e))
        break
    
wav.close()
audio_out.deinit()
print('Done')