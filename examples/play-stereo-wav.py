#
# This file is part of the MicroPython ESP32 project
# 
# The MIT License (MIT)
#
# Copyright (c) 2019 Mike Teachman
#
# https://opensource.org/licenses/MIT

# This example reads audio samples from a WAV file
# and writes them to a stereo audio DAC that supports the I2S protocol.
#
# Testing was done with an I2S PCM5102 Stereo DAC Decoder breakout board
#
# A sample WAV file "side-to-side-8k-16bits-stereo.wav" is included in the 
# wav_files folder.  The sample consists of a single-frequency tone that alternates
# between the left and right channels.  It can be copied to the internal filesystem using
# a command line tool such as rshell or ampy
#
# The WAV file will play continuously until a keyboard interrupt is detected or
# the ESP32 is reset

from machine import I2S
from machine import Pin

SAMPLES_PER_SECOND = 8000

bck_pin = Pin(22)
ws_pin = Pin(2)
sdout_pin = Pin(21)

# channelformat settings:
#    stereo WAV:  channelformat=I2S.RIGHT_LEFT
#    mono WAV:    channelformat=I2S.ONLY_RIGHT
audio_out = I2S(I2S.NUM1, bck=bck_pin, ws=ws_pin, sdout=sdout_pin, 
              standard=I2S.PHILIPS, mode=I2S.MASTER_TX,
              dataformat=I2S.B16, channelformat=I2S.RIGHT_LEFT,
              samplerate=SAMPLES_PER_SECOND,
              dmacount=16, dmalen=512)

s = open('side-to-side-8k-16bits-stereo.wav','rb')
s.seek(44) # advance to first byte of Data section in WAV file

# continuously read audio samples from the WAV file 
# and write them to an I2S peripheral
while True:
    try:
        audio_samples = bytearray(s.read(2048))
        numwritten = 0
        # end of WAV file?    
        if len(audio_samples) == 0:
            s.seek(44) # advance to first byte of Data section
        else:
            # block until all buffer samples are written
            numwritten = audio_out.write(audio_samples)
    except KeyboardInterrupt:  
        s.close()
        audio_out.deinit()
        break            