# SKN26-3rd-4Team

---

# 💬 감정 기반 연인 갈등 완화 대화 추천 시스템

---

## 📌 목차

1. [Team](#-team)
2. [프로젝트 개요](#프로젝트-개요)
3. [시스템 아키텍처](#시스템-아키텍처)
4. [데이터 전처리 결과](#데이터-전처리-결과)
5. [RAG 기반 시스템 구현](#rag-기반-시스템-구현)
6. [테스트 및 평가](#테스트-및-평가)
7. [Streamlit UI](#streamlit-ui)
8. [프로젝트 구조](#프로젝트-구조)
9. [동료 회고](#동료-회고)

---

## 1.  Team

## 🎁 Andy's Data Box

<table align="center">
  <tr>
    <td align="center" width="125" valign="top">
      <table align="center" width="105">
        <tr>
          <td align="center" height="120">
            <img src=figures/렉스.jpg
                 width="70" height="95"
                 style="object-fit:contain;">
          </td>
        </tr>
        <tr>
          <td align="center" height="36"><b>김용욱</b></td>
        </tr>
        <tr>
          <td align="center" height="44">
            <a href="https://github.com/yonguk12077-beep">@yonguk12077-beep</a>
          </td>
        </tr>
      </table>
    </td>
    <td align="center" width="125" valign="top">
      <table align="center" width="105">
        <tr>
          <td align="center" height="120">
            <img src="figures/우디.jpg"
                 width="70" height="95"
                 style="object-fit:contain;">
          </td>
        </tr>
        <tr>
          <td align="center" height="36"><b>박소윤</b></td>
        </tr>
        <tr>
          <td align="center" height="44">
            <a href="https://github.com/parksoyun9084-cloud">@parksoyun9084-cloud</a>
          </td>
        </tr>
      </table>
    </td>
    <td align="center" width="125" valign="top">
      <table align="center" width="105">
        <tr>
          <td align="center" height="120">
            <img src="figures/미스터샤크.jpg"
                 width="70" height="95"
                 style="object-fit:contain;">
          </td>
        </tr>
        <tr>
          <td align="center" height="36"><b>윤찬호</b></td>
        </tr>
        <tr>
          <td align="center" height="44">
            <a href="https://github.com/ch3477-sudo">@ch3477-sudo</a>
          </td>
        </tr>
      </table>
    </td>
    </td>
    <td align="center" width="125" valign="top">
      <table align="center" width="105">
        <tr>
          <td align="center" height="120">
            <img src="figures/미스터감자.jpg"
                 width="70" height="95"
                 style="object-fit:contain;">
          </td>
        </tr>
        <tr>
          <td align="center" height="36"><b>이선호</b></td>
        </tr>
        <tr>
          <td align="center" height="44">
            <a href="https://github.com/fridayeverynote-cell">@fridayeverynote-cell</a>
          </td>
        </tr>
      </table>
    </td>
    <td align="center" width="125" valign="top">
      <table align="center" width="105">
        <tr>
          <td align="center" height="120">
            <img src="figures/저그 황제.jpg"
                 width="70" height="95"
                 style="object-fit:contain;">
          </td>
        </tr>
        <tr>
          <td align="center" height="36"><b>전승권</b></td>
        </tr>
        <tr>
          <td align="center" height="44">
            <a href="https://github.com/eaent">@eaent</a>
          </td>
        </tr>
      </table>
</table>


| 이름 | 역할 |
|------|------|
| 김용욱 | RAG 파이프라인 구축 |
| 박소윤 | 기획 총괄 / UI 설계 / 프로젝트 관리 |
| 윤찬호 | 데이터 전처리 및 Retrieval 평가 |
| 전승권 | 환경설정 / API / 앱 구조 |
| 이선호 | |

---

## 2. 프로젝트 개요

연인 간 대화에서 발생하는 갈등 상황을 분석하고,  
감정 및 위험도를 기반으로 적절한 대화 답변을 추천하는 시스템 구축



---

## 3. 시스템 아키텍처

- 입력: 사용자 대화
- 감정 분석
- 위험도 분석
- RAG 기반 유사 사례 검색
- 답변 생성

---

## 4. 데이터 전처리 결과

- 공감형 대화 데이터셋 활용
- 연인 관계 대화 필터링
- 발화 단위 구조화
- CSV / JSON 형태로 변환
- RAG 학습용 문서 생성

---

## 5. RAG 기반 시스템 구현

- Embedding 모델 적용
- Vector DB 구축 (FAISS / 예정: Pinecone)
- Retriever 구성
- Prompt 기반 답변 생성

---

## 6. 테스트 및 평가

- BM25 / Dense / RRF 비교
- 감정 유사도 평가
- 검색 정확도 분석
- RAG vs Baseline 비교

---

## 7. Streamlit UI

- 채팅 인터페이스
- 감정 / 위험도 카드
- 추천 답변 출력

---

## 8. 프로젝트 구조

```
project/
│
├─ data/
│   ├─ raw/
│   └─ processed/
│
├─ src/
│   ├─ data/
│   ├─ emotion/
│   ├─ rag/
│   └─ utils/
│
├─ app/
│   └─ streamlit_app.py
│
├─ docs/
│
└─ README.md
```

---

## 9. 동료 회고

<table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd; margin-bottom: 30px;">
    <thead>
        <tr style="background-color: #f8f9fa;">
            <th style="width: 15%; border: 1px solid #ddd; padding: 10px;">작성자</th>
            <th style="width: 15%; border: 1px solid #ddd; padding: 10px;">대상자</th>
            <th style="border: 1px solid #ddd; padding: 10px;">회고 내용</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td rowspan="4" style="text-align: center; font-weight: bold; border: 1px solid #ddd;">김용욱</td>
            <td style="text-align: center; border: 1px solid #ddd;">박소윤</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
        <tr>
            <td style="text-align: center; border: 1px solid #ddd;">윤찬호</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
        <tr>
            <td style="text-align: center; border: 1px solid #ddd;">이선호</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
        <tr>
            <td style="text-align: center; border: 1px solid #ddd;">전승권</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
<table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd; margin-bottom: 30px;">
    <thead>
        <tr style="background-color: #f8f9fa;">
            <th style="width: 15%; border: 1px solid #ddd; padding: 10px;">작성자</th>
            <th style="width: 15%; border: 1px solid #ddd; padding: 10px;">대상자</th>
            <th style="border: 1px solid #ddd; padding: 10px;">회고 내용</th>
        </tr>
    </thead>
        <tr>
            <td rowspan="4" style="text-align: center; font-weight: bold; border: 1px solid #ddd;">박소윤</td>
            <td style="text-align: center; border: 1px solid #ddd;">김용욱</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
        <tr>
            <td style="text-align: center; border: 1px solid #ddd;">윤찬호</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
        <tr>
            <td style="text-align: center; border: 1px solid #ddd;">이선호</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
        <tr>
            <td style="text-align: center; border: 1px solid #ddd;">전승권</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
<table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd; margin-bottom: 30px;">
    <thead>
        <tr style="background-color: #f8f9fa;">
            <th style="width: 15%; border: 1px solid #ddd; padding: 10px;">작성자</th>
            <th style="width: 15%; border: 1px solid #ddd; padding: 10px;">대상자</th>
            <th style="border: 1px solid #ddd; padding: 10px;">회고 내용</th>
        </tr>
    </thead>
        <tr>
            <td rowspan="4" style="text-align: center; font-weight: bold; border: 1px solid #ddd;">윤찬호</td>
            <td style="text-align: center; border: 1px solid #ddd;">김용욱</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
        <tr>
            <td style="text-align: center; border: 1px solid #ddd;">박소윤</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
        <tr>
            <td style="text-align: center; border: 1px solid #ddd;">이선호</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
        <tr>
            <td style="text-align: center; border: 1px solid #ddd;">전승권</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
<table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd; margin-bottom: 30px;">
    <thead>
        <tr style="background-color: #f8f9fa;">
            <th style="width: 15%; border: 1px solid #ddd; padding: 10px;">작성자</th>
            <th style="width: 15%; border: 1px solid #ddd; padding: 10px;">대상자</th>
            <th style="border: 1px solid #ddd; padding: 10px;">회고 내용</th>
        </tr>
    </thead>
        <tr>
            <td rowspan="4" style="text-align: center; font-weight: bold; border: 1px solid #ddd;">이선호</td>
            <td style="text-align: center; border: 1px solid #ddd;">김용욱</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
        <tr>
            <td style="text-align: center; border: 1px solid #ddd;">박소윤</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
        <tr>
            <td style="text-align: center; border: 1px solid #ddd;">윤찬호</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
        <tr>
            <td style="text-align: center; border: 1px solid #ddd;">전승권</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
<table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd; margin-bottom: 30px;">
    <thead>
        <tr style="background-color: #f8f9fa;">
            <th style="width: 15%; border: 1px solid #ddd; padding: 10px;">작성자</th>
            <th style="width: 15%; border: 1px solid #ddd; padding: 10px;">대상자</th>
            <th style="border: 1px solid #ddd; padding: 10px;">회고 내용</th>
        </tr>
    </thead>
        <tr>
            <td rowspan="4" style="text-align: center; font-weight: bold; border: 1px solid #ddd;">전승권</td>
            <td style="text-align: center; border: 1px solid #ddd;">김용욱</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
        <tr>
            <td style="text-align: center; border: 1px solid #ddd;">박소윤</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
        <tr>
            <td style="text-align: center; border: 1px solid #ddd;">윤찬호</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
        <tr>
            <td style="text-align: center; border: 1px solid #ddd;">이선호</td>
            <td style="border: 1px solid #ddd; padding: 10px;"></td>
        </tr>
    </tbody>
</table>