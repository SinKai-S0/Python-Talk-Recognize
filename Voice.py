import os
import time
import logging
from io import BytesIO
from ctypes import CDLL
from pathlib import Path
from pprint import pprint
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from typing import NamedTuple

CDLL(str(Path("include/onnxruntime-win-x64-1.16.1/lib/onnxruntime.dll").resolve(strict=True)))
CDLL(str(Path("include/onnxruntime-win-x64-1.16.1/lib/onnxruntime_providers_shared.dll").resolve(strict=True)))

# 参考
# https://github.com/juu7g/Python-voice-input/blob/main/voice_input_juu7g/voice_input_Sphinx.py

import speech_recognition as sr
from voicevox_core import VoicevoxCore, AccelerationMode, METAS
from pydub import AudioSegment
from pydub.playback import play

format = "%(levelname)-9s  %(asctime)s [%(filename)s:%(lineno)-5d] %(message)s"
logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
st_handler = logging.StreamHandler()
fl_handler = logging.FileHandler(filename=os.path.basename(__file__)+".log",encoding="utf-8")
st_handler.setLevel(logging.DEBUG)
fl_handler.setLevel(logging.WARNING)
st_handler.setFormatter(logging.Formatter(format))
fl_handler.setFormatter(logging.Formatter(format))
logger.addHandler(st_handler)
logger.addHandler(fl_handler)


class VoiceRecognizer:
    def __init__(self,device:int=None,talk=True) -> None:
        """
        Recognizerをリアルタイムで実行する
        
        voicevox_coreとの連携で喋らせることも可能
        
        args:
            device: デバイスインデックス Pyaudioに依存
            talk: 喋らせるかどうか
        """
        self.rec = sr.Recognizer()
        self.mic = sr.Microphone(device_index=device)
        self.vvox = VoiceVoxTalk()
        self.futures_limit = 10
        self.futures = []
        self.pool = ThreadPoolExecutor(3,thread_name_prefix="Rec Thread")
        self.bg_listen_stop = None
        self.output = None
        self.talk_flag = talk
        
        
    def recognize_voice_thread_pool(self,audio):
        """
        スレッド処理実行
        
        args:
            audio:音声データ
        """
        logger.debug("<Recognize Submit>")
        future = self.pool.submit(self.recognize_voice,audio,self.output)
        if self.talk_flag:
            future.add_done_callback(self.talk)
        self.futures.append(future)
        
        
    def recognize_voice(self,audio,output=None) -> str:
        """
        音声分析
        
        args:
            audio:音声データ
            output:出力ファイルパス (*.txt)
        """
        text = ""
        try:
            logger.debug("<Recognize Start>")
            text = self.rec.recognize_google(audio,language="ja-JP")
            logger.debug(text)
            if output:
                with open(output,"a") as f:
                    f.write(text+"\n")
        except sr.UnknownValueError:
            logger.debug("<Recognize UnknownValue>")
        except sr.RequestError:
            pass
        logger.debug("<Recognize Finished>")
        return text
    
    
    def listen_voice(self,timelimit=None):
        """
        音声を検知するまで待ってから分析を開始する
        
        args:
            timelimit:音声を検知してから録音する秒数
        """
        logger.debug("<Listen Start>")
        with self.mic as source:
            self.rec.adjust_for_ambient_noise(source)
            audio = self.rec.listen(source,phrase_time_limit=timelimit)
        logger.debug("<Listen Finished>")
        if not self.pool._shutdown:
            self.recognize_voice_thread_pool(audio)
            
        return audio
    
    
    def listen_voice_in_bg(self,timelimit=None):
        """
        音声を検知し終わった時にコールバック実行(スレッドを利用している)
        
        リアルタイムで音声取るならこっちのほうが良いかも
        
        args:
            timelimit:音声を検知してから録音する秒数
        """
        logger.debug("<BackGround Listen Start>")
        with self.mic as source:
            self.rec.adjust_for_ambient_noise(source)
        self.bg_listen_stop = self.rec.listen_in_background(
            self.mic,
            lambda rec,audio:self.recognize_voice_thread_pool(audio),
            phrase_time_limit = timelimit
            )


    def stop_bg(self):
        """
        Recognizer.listen_in_backgroundを停止する
        """
        if self.bg_listen_stop is not None:
            self.bg_listen_stop(False)
            self.bg_listen_stop = None
            logger.debug("<BackGround Listen Stopped>")
            
        
    def talk(self,future):
        """
        VoiceVoxとの連携でテキストを喋らせる(ThreadPoolExecutorコールバック用)
        """
        self.vvox.speak_thread_pool(future.result())
        if len(self.futures) > self.futures_limit:
            self.futures.pop(0)
            
            
    def change_device(self,n):
        self.stop_bg()
        if n is None:
            mic = sr.Microphone()
        else:
            try:
                mic = sr.Microphone(n)
                logger.debug("<Device Test 'Please Speak'>")
                with mic as souce:
                    self.rec.listen(souce,timeout=10)
                logger.debug("<Device Test OK>")
            except:
                logger.debug("<Device Test Error'>")
                mic = sr.Microphone()
        self.mic = mic
        
    def set_output(self,path):
        self.output = path
    
    def set_talk(self,value:bool):
        self.talk_flag = value
    
    def shutdown(self):
        self.pool.shutdown()
        self.vvox.shutdown()


class VoiceVoxTalk:
    def __init__(self) -> None:
        self.futures = []
        self.pool = ThreadPoolExecutor(1,thread_name_prefix="VVOX Talk Thread")
        self.lock = Lock()
        
        self.openjtalk = "include/open_jtalk_dic_utf_8-1.11"
        self.core = VoicevoxCore(
            acceleration_mode=AccelerationMode.AUTO,
            open_jtalk_dict_dir=Path(self.openjtalk),
            )
        self.speaker_id = 0
        self.speakers = self.get_speakers()
        self.output = None

    
    def speak(self,text,lock):
        """
        ファイルを出力しないで喋らせる(BytesIO)
        
        args:
            text:テキスト
            lock:Thread.Lock
        """
        if not text:
            return
        logger.debug("<Speak Start>")
        try:
            with lock:
                self.reload_speaker()
                s_t = time.time()
                # wav = self.core.tts(text,self.speaker_id)
                wav = self.synthesis(text)
                logger.debug(f"<Synthesis EndTime {time.time()-s_t}>")
                byte = BytesIO(wav)
                segment = AudioSegment.from_wav(byte)
                logger.debug("<Playing>")
                play(segment)
        except Exception as e:
            logger.debug(f"<Speak Error>\n{e}")
        logger.debug("<Speak Finished>")
    
    
    def synthesis(self,text):
        """
        音声合成（時間がかかる上、ブロッキング発生）
        """
        logger.debug("<VVOX Query>")
        query = self.core.audio_query(text,self.speaker_id)
        logger.debug("<VVOX Synthesis>")
        wav = self.core.synthesis(query,self.speaker_id)
        return wav
    
    
    def speak_thread_pool(self,text):
        """
        スレッドプールに喋る処理を投げる
        
        args:
            text:テキスト
        """
        if not text:
            return
        logger.debug("<Speak Submit>")
        future = self.pool.submit(self.speak,text,self.lock)
        # self.futures.append(future)
        # Thread(target=self.speak, args=(text,self.lock,)).start()
    
    
    def get_speakers(self):
        """
        Voicevox.METASからspeakerを取得、データ整形
        
        returns:
            list:Speakers(id,name,style)
        """
        speakers = []
        for i in METAS:
            speakers += [Speakers(s.id,i.name,s.name) for s in i.styles]
        speakers.sort(key=lambda x:x.id)
        # pprint(speakers)
        return speakers
    
    
    def change_speaker(self,_id):
        """
        speaker_idをspeaker内の数値にする
        
        args:
            _id:speaker_id
        """
        self.speaker_id = min(len(self.speakers)-1,max(_id, 0))
        # self.reload_speaker()
            
    
    def reload_speaker(self):
        """
        speakerを読み込みなおす
        """
        if not self.core.is_model_loaded(self.speaker_id):
            logger.debug("<Reload Speaker Start>")
            self.core.load_model(self.speaker_id)
            logger.debug("<Reload Speaker Finished>")
            
        
    def shutdown(self):
        self.pool.shutdown()


class Speakers(NamedTuple):
    id:int
    name:str
    style:str
        
        
        

def main():
    v = VoiceRecognizer()
    v.listen_voice_in_bg()
    # vvox = VoiceVoxTalk()
    result = []
    try:
        while True:
            for future in v.futures:
                if not future.done():
                    continue
                result = future.result()
                print(result)
    except KeyboardInterrupt:
        print("Exit")
        pass

if __name__ == "__main__":
    main()
