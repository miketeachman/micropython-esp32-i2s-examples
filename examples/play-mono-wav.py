#
# This file is part of the MicroPython ESP32 project
# 
# The MIT License (MIT)
#
# Copyright (c) 2019 Mike Teachman
#
# https://opensource.org/licenses/MIT

# This example reads audio samples from a WAV file
# and writes them to a mono audio DAC that supports the I2S protocol
#
# Testing was done with an Adafruit I2S 3W Class D Amplifier Breakout - MAX98357A
#
# A sample WAV file "taunt-16k-16bits-mono-12db.wav" is included in the 
# wav_files folder.  It can be copied to the internal filesystem using
# a command line tool such as rshell or ampy
#
# The WAV file will play continuously until a keyboard interrupt is detected or
# the ESP32 is reset
#
# The I2S write method sets the optional timeout argument to 0.  In this 
# configuration the write method will return immediately when no DMA memory space is
# available to copy the samples from the audio_samples buffer
  
from machine import I2S
from machine import Pin

SAMPLES_PER_SECOND = 16000

bck_pin = Pin(32) 
ws_pin = Pin(33)  
sdout_pin = Pin(25)

# channelformat settings:
#    stereo WAV:  channelformat=I2S.RIGHT_LEFT
#    mono WAV:    channelformat=I2S.ONLY_RIGHT
audio_out = I2S(I2S.NUM1, bck=bck_pin, ws=ws_pin, sdout=sdout_pin, 
              standard=I2S.PHILIPS, mode=I2S.MASTER_TX,
              dataformat=I2S.B16, channelformat=I2S.ONLY_RIGHT,
              samplerate=SAMPLES_PER_SECOND,
              dmacount=8, dmalen=512)

s = open('taunt-16k-16bits-mono-12db.wav','rb')
s.seek(44) # advance to first byte of Data section in WAV file

# continuously read audio samples from the WAV file 
# and write them to an I2S DAC
while True:
    try:
        audio_samples = bytearray(s.read(1024))
        numwritten = 0
        # end of WAV file?    
        if len(audio_samples) == 0:
            s.seek(44) # advance to first byte of Data section
        else:
            # loop until samples can be written to DMA
            while numwritten == 0:
                # return immediately when no DMA buffer is available (timeout=0)
                numwritten = audio_out.write(audio_samples, timeout=0)
                
                # await - allow other coros to run   
    except KeyboardInterrupt:  
        s.close()
        audio_out.deinit()
        break