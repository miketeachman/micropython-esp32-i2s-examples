# The MIT License (MIT)
# Copyright (c) 2020 Mike Teachman
# https://opensource.org/licenses/MIT

# Purpose:
# - read 16-bit audio samples from a mono formatted WAV file on SD card
# - write audio samples to an I2S amplifier or DAC module 
#
# Uasyncio:
# - two co-routines are demonstrated
#    - play the WAV file
#    - write text to the REPL
# - Uasyncio version >= 3 is needed for this example
#
# Sample WAV files in wav_files folder:
#   "taunt-16k-16bits-mono.wav"
#   "taunt-16k-16bits-mono-12db.wav" (lower volume version)
#
# Hardware tested:
# - MAX98357A amplifier module (Adafruit I2S 3W Class D Amplifier Breakout)
# - PCM5102 stereo DAC module
#
# The WAV file will play continuously until a keyboard interrupt is detected or
# the ESP32 is reset
  
from machine import I2S
from machine import SDCard
from machine import Pin
import uasyncio as asyncio

if (asyncio.__version__)[0] < 3:
    raise ImportError ('example requires uasyncio verion >= 3')

#======= USER CONFIGURATION =======
WAV_FILE = 'taunt-16k-16bits-mono-12db.wav'
SAMPLE_RATE_IN_HZ = 16000
#======= USER CONFIGURATION =======

async def play_wav():
    bck_pin = Pin(21) 
    ws_pin = Pin(22)  
    sdout_pin = Pin(27)
    
    # channelformat settings:
    #     mono WAV:  channelformat=I2S.ONLY_LEFT
    audio_out = I2S(
        I2S.NUM0, 
        bck=bck_pin, ws=ws_pin, sdout=sdout_pin, 
        standard=I2S.PHILIPS, 
        mode=I2S.MASTER_TX,
        dataformat=I2S.B16, 
        channelformat=I2S.ONLY_LEFT,
        samplerate=SAMPLE_RATE_IN_HZ,
        dmacount=10, dmalen=512)
    
    # configure SD card
    #   slot=2 configures SD card to use the SPI3 controller (VSPI), DMA channel = 2
    #   slot=3 configures SD card to use the SPI2 controller (HSPI), DMA channel = 1
    sd = SDCard(slot=3, sck=Pin(18), mosi=Pin(23), miso=Pin(19), cs=Pin(4))
    uos.mount(sd, "/sd")
    wav_file = '/sd/{}'.format(WAV_FILE)
    wav = open(wav_file,'rb')
    
    # advance to first byte of Data section in WAV file
    pos = wav.seek(44) 
    
    # allocate sample arrays
    #   memoryview used to reduce heap allocation in while loop
    wav_samples = bytearray(1024)
    wav_samples_mv = memoryview(wav_samples)
    
    print('Starting ... ')
    # continuously read audio samples from the WAV file 
    # and write them to an I2S DAC
    
    try:
        while True:
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
            await asyncio.sleep_ms(10)
    except (KeyboardInterrupt, Exception) as e:
        print('caught exception {} {}'.format(type(e).__name__, e))
        raise
    finally:
        wav.close()
        uos.umount("/sd")
        sd.deinit()
        audio_out.deinit()
        print('Done')

async def another_coro():
    i = 0
    while True:
        print(i)
        i+=1
        await asyncio.sleep(1)

async def main():
    play_wav_task = asyncio.create_task(play_wav())
    another_task = asyncio.create_task(another_coro())
    while True:
        await asyncio.sleep(1)
        
asyncio.run(main())