# DICOM_viewer
実習課題として作成したDICOMファイルのViewrです。


## 作成した環境
Visual Studio Code
## ファイル構成
```
DICOM_viewr_vX.exe #実行ファイル
viewr_main.py #ソースコード
```

## 実行環境
venvの仮想環境のセットアップ(Windowsを想定)
```
python3 -m venv .venv
.venv/Scripts/activate
```
依存関係のインストール
```
pip install -r requirements.txt
```

DICOMファイルの保存先 <br>
[DICOM_Folder]フォルダを[DICOM_Viewer_vX.exe]と同じ階層に作成し、その中に保存してください。 ※ vX の X はバージョン番号で読み替えてください。<br>
![temp_loc](./Images/loc_temp.png)

※.exeファイルが正常に動作しない場合(Download Zipでダウンロードした場合を想定)は<br>
解凍したファイルの[viewr_main.py]と同じ階層に[DICOM_Folder]を作成し、その中に画像を保存した上で、<br>
VScode上など、上記の仮想環境と依存関係を用意したうえで、下記を.venvの仮想環境上でターミナルから実行してください。<br>
```
python viewr_main.py
```

## 内容説明
ダウンロードした[DICOM_Viwer_vX.exe]をダブルクリックして起動します。<br>
同じ階層に用意した[DICOM_Folder]内のDICOMファイルを参照して画面に表示します。<br>

アプリ画面
![demo](./Images/app_demo.png)
<br>
アプリ右側の説明 <br>
![right_setting](./Images/control.png)

アプリ左側の説明 <br>
画面上で[ctrl]+[マウスホイールの回転]を使用することで、マウスポインタの位置を基準に拡大縮小の率を変更することができます。<br>
画面上で左クリックを押しながら、マウスポインタを動かすことで、表示位置を動かすことができます。<br>


## ライセンス
Copyright (c) 2026 Nakano0830
Released under the MIT license
https://opensource.org/licenses/mit-license.php
