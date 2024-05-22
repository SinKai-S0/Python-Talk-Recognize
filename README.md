# Python-Talk-Recognize

## 概要
音声文字起こしツール
音声入力から分析した結果をファイルに出力します
読み上げ機能付き

## 環境
Python 3.11.3  
[Voicevox-core](https://github.com/VOICEVOX/voicevox_core) 0.15.0+cpu (読み上げ)
[onnxruntime](https://github.com/microsoft/onnxruntime/releases/tag/v1.16.3)
- (必要) include/onnxruntime-win-x64-1.16.1/lib/onnxruntime.dll
- (必要) include/onnxruntime-win-x64-1.16.1/lib/onnxruntime_providers_shared.dll
[open_jtalk](https://sourceforge.net/projects/open-jtalk/)

pygame 2.5.2 (GUI)  
SpeechRecognition 3.10.1 (音声分析)  
pydub 0.25.1 (wav読み込み)  
