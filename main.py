from pprint import pprint
from typing import NamedTuple

# インストールが必要なモノ
import pygame
from pyaudio import PyAudio
# 自作
from Voice import VoiceRecognizer as VRec
# from Voice_noblocking import VoiceRecognizer as NoBlockVRec


pygame.init()
WHITE = (255,255,255)
BLACK = (0,0,0)
DISPLAY = pygame.Rect(0,0,1920//2,1080//2)


class Fonts(NamedTuple):
    ja = pygame.font.SysFont("meiryo",40//2)
    en = pygame.font.SysFont("arial",50)

class SoundDeviceFull(NamedTuple):
    """データ整形用
    """
    name:str
    index:int
    hostApi:int
    maxInputChannels:int
    maxOutputChannels:int
    defaultHighInputLatency:float
    defaultHighOutputLatency:float
    defaultLowInputLatency:float
    defaultLowOutputLatency:float
    defaultSampleRate:float
    structVersion:int

class SoundDevice(NamedTuple):
    """データ整形用
    """
    index:int
    name:str


def get_devices():
    p = PyAudio()
    i_device = []
    o_device = []
    d = []
    for i in range(p.get_device_count()):
        device = p.get_device_info_by_index(i)
        if device["maxOutputChannels"] != 0:
            # o_device.append(SoundDeviceFull(**device))
            o_device.append(SoundDevice(device["index"],device["name"]))
        if device["maxInputChannels"] != 0:
            # i_device.append(SoundDeviceFull(**device))
            i_device.append(SoundDevice(device["index"],device["name"]))
    # pprint(sorted(o_device,key=lambda x:x.name))
    # pprint(sorted(i_device,key=lambda x:x.name))
    return i_device,o_device


def main():
    screen = pygame.display.set_mode(DISPLAY.size)
    surface = pygame.display.get_surface()
    quit_flag = False
    rec_flag = False
    talk_flag = True
    state_flag = 0
    input_device = 0
    input_devices = [SoundDevice(None,"Default")]+get_devices()[0]
    voice_rec = VRec()
    voice_rec.set_output("output.txt")
    speakers = voice_rec.vvox.get_speakers()
    speaker_id = voice_rec.vvox.speaker_id
    while not quit_flag:
        screen.fill(BLACK)
        txtlist = []
        txt = f"[0] Recorder | [1] Device Change"
        txtlist.append(Fonts.ja.render(txt, True, WHITE, BLACK))
        if state_flag == 0:
            txt = f"Recorder"
            txtlist.append(Fonts.ja.render(txt, True, WHITE, BLACK))
            txt = f"[T] Talk = {talk_flag} | [←][→] "
            txt += f"{speakers[speaker_id]}{'[Lock]' if rec_flag else ''}"
            txtlist.append(Fonts.ja.render(txt, True, WHITE, BLACK))
            txt = f"[R] Rec = {rec_flag}"
            txtlist.append(Fonts.ja.render(txt, True, WHITE, BLACK))
            txt = f"is_Speaking = {voice_rec.vvox.lock.locked()} | Futures = {len(voice_rec.futures)}"
            txtlist.append(Fonts.ja.render(txt, True, WHITE, BLACK))
        elif state_flag == 1:
            txt = f"Device Change"
            txtlist.append(Fonts.ja.render(txt, True, WHITE, BLACK))
            txt = f"[←][→] [Z] Select | {input_devices[input_device].name}"
            txtlist.append(Fonts.ja.render(txt, True, WHITE, BLACK))
        for future in voice_rec.futures:
            txtlist.append(Fonts.ja.render(f"{future.result()}", True, BLACK, WHITE))
        row = 0
        for txt in txtlist:
            txtrect = screen.blit(txt, (10, row))
            row += txtrect.bottom - txtrect.top
        
        # 特定の入力デバイスに変えると連続でsubmitされて操作不可能になるのでその防止
        if len(voice_rec.futures) > voice_rec.futures_limit:
            rec_flag = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: quit_flag = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: quit_flag = True
                elif event.key == pygame.K_0: state_flag = 0 # Recording モード
                elif event.key == pygame.K_1: state_flag = 1 # Device Change モード
                elif event.key == pygame.K_2: state_flag = 2 
                if state_flag == 0:
                    # Record 開始/停止
                    if event.key == pygame.K_r:
                        if rec_flag:
                            voice_rec.stop_bg()
                        else:
                            voice_rec.listen_voice_in_bg(timelimit=10)                        
                        rec_flag = not rec_flag
                    # Talkモード オン/オフ
                    elif event.key == pygame.K_t:
                        talk_flag = not talk_flag
                        voice_rec.set_talk(talk_flag)
                    if not rec_flag:
                        if event.key == pygame.K_LEFT:
                            speaker_id = min(len(speakers)-1, max(speaker_id - 1, 0))
                            voice_rec.vvox.change_speaker(speaker_id)
                        elif event.key == pygame.K_RIGHT:
                            speaker_id = min(len(speakers)-1, speaker_id + 1)
                            voice_rec.vvox.change_speaker(speaker_id)
                elif state_flag == 1:
                    if not rec_flag:
                        if event.key == pygame.K_LEFT:
                            input_device = min(len(input_devices) - 1, max(input_device - 1, 0))
                        elif event.key == pygame.K_RIGHT:
                            input_device = min(len(input_devices) - 1, input_device + 1)
                        elif event.key == pygame.K_z:
                            voice_rec.change_device(input_devices[input_device].index)
                
                
        pygame.display.update()
    
    if rec_flag:voice_rec.stop_bg()
    voice_rec.shutdown()
    
    
    

if __name__ == "__main__":
    # get_devices()
    main()
    # test_noblocking()