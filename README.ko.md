[Automatic1111 웹UI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)를 위한 태깅(라벨링) 확장 기능
---
DeepDanbooru 와 같은 모델을 통해 단일 또는 여러 이미지로부터 부루에서 사용하는 태그를 알아냅니다.

[You don't know how to read Korean? Read it in English here!](README.original.md)

## 들어가기 앞서
모델과 대부분의 코드는 제가 만들지 않았고 [DeepDanbooru](https://github.com/KichangKim/DeepDanbooru) 와 MrSmillingWolf 의 태거에서 가져왔습니다.

## 설치하기
1. *확장기능* -> *URL로부터 확장기능 설치* -> 이 레포지토리 주소 입력 -> *설치*
   - 또는 이 레포지토리를 `extensions/` 디렉터리 내에 클론합니다.
      ```sh
      $ git clone https://github.com/picobyte/stable-diffusion-webui-wd14-tagger.git extensions/tagger
      ```

1. 모델 추가하기
   - #### *MrSmilingWolf's model (a.k.a. Waifu Diffusion 1.4 tagger)*
      처음 실행할 때 [HuggingFace 레포지토리](https://huggingface.co/SmilingWolf/wd-v1-4-vit-tagger)로부터 자동으로 받아옵니다.

      모델과 관련된 또는 추가 학습에 대한 질문은 원작자인 MrSmilingWolf#5991 으로 물어봐주세요.

   - #### *DeepDanbooru*
      1. 다양한 모델 파일은 아래 주소에서 찾을 수 있습니다.
         - [DeepDanbooru model](https://github.com/KichangKim/DeepDanbooru/releases)
         - [e621 model by 🐾Zack🐾#1984](https://discord.gg/BDFpq9Yb7K)
            *(NSFW 주의!)*

      1. 모델과 설정 파일이 포함된 프로젝트 폴더를 `models/deepdanbooru` 경로로 옮깁니다.

      1. 파일 구조는 다음과 같습니다:
         ```
         models/
         └╴deepdanbooru/
           ├╴deepdanbooru-v3-20211112-sgd-e28/
           │ ├╴project.json
           │ └╴...
           │
           ├╴deepdanbooru-v4-20200814-sgd-e30/
           │ ├╴project.json
           │ └╴...
           │
           ├╴e621-v3-20221117-sgd-e32/
           │ ├╴project.json
           │ └╴...
           │
           ...
         ```

1. 웹UI 를 시작하거나 재시작합니다.
   - 또는 *Interrogator* 드롭다운 상자 우측에 있는 새로고침 버튼을 누릅니다.


## 스크린샷
![Screenshot](docs/screenshot.png)

Artwork made by [hecattaart](https://vk.com/hecattaart?w=wall-89063929_3767)

## 저작권

빌려온 코드(예: `dbimutils.py`)를 제외하고 모두 Public domain 
