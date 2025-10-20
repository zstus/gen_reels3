"""
영어 및 다국어 단어를 한글 발음으로 매핑하는 사전 클래스
"""
import os
import json


class PronunciationDictionary:
    """다국어 단어 → 한글 발음 변환 사전"""

    def __init__(self):
        # 기본 사전 (확장 가능)
        self.dictionary = {
            # 약어 및 두문자어
            'LAS': '라스',
            'AI': '에이아이',
            'ML': '엠엘',
            'API': '에이피아이',
            'CPU': '씨피유',
            'GPU': '지피유',
            'USB': '유에스비',
            'URL': '유알엘',
            'HTML': '에이치티엠엘',
            'CSS': '씨에스에스',
            'JSON': '제이슨',
            'SQL': '에스큐엘',
            'REST': '레스트',
            'HTTP': '에이치티티피',
            'HTTPS': '에이치티티피에스',
            'FTP': '에프티피',
            'DNS': '디엔에스',
            'VPN': '브이피엔',
            'IT': '아이티',
            'PC': '피씨',
            'TV': '티비',
            'DVD': '디브이디',
            'CD': '씨디',
            'MP3': '엠피쓰리',
            'MP4': '엠피포',
            'PDF': '피디에프',
            'ZIP': '집',
            'RAM': '램',
            'ROM': '롬',
            'SSD': '에스에스디',
            'HDD': '에이치디디',

            # 기술 용어
            'Python': '파이썬',
            'JavaScript': '자바스크립트',
            'Java': '자바',
            'TypeScript': '타입스크립트',
            'React': '리액트',
            'Vue': '뷰',
            'Angular': '앵귤러',
            'Node': '노드',
            'Docker': '도커',
            'Kubernetes': '쿠버네티스',
            'AWS': '에이더블유에스',
            'Azure': '애저',
            'GCP': '지씨피',
            'Linux': '리눅스',
            'Windows': '윈도우',
            'Mac': '맥',
            'iOS': '아이오에스',
            'Android': '안드로이드',

            # 기업 및 서비스
            'Netflix': '넷플릭스',
            'YouTube': '유튜브',
            'Google': '구글',
            'Facebook': '페이스북',
            'Instagram': '인스타그램',
            'Twitter': '트위터',
            'TikTok': '틱톡',
            'Amazon': '아마존',
            'Apple': '애플',
            'Microsoft': '마이크로소프트',
            'Samsung': '삼성',
            'LG': '엘지',
            'Naver': '네이버',
            'Kakao': '카카오',
            'Zoom': '줌',
            'Slack': '슬랙',
            'GitHub': '깃허브',
            'GitLab': '깃랩',
            'KB': '케이비',

            # 제품명
            'iPhone': '아이폰',
            'iPad': '아이패드',
            'MacBook': '맥북',
            'Galaxy': '갤럭시',
            'Pixel': '픽셀',
            'Surface': '서피스',
            'PlayStation': '플레이스테이션',
            'Xbox': '엑스박스',
            'Switch': '스위치',
            'PC': '피씨',

            # 일반 영어 단어
            'Hello': '헬로',
            'World': '월드',
            'Service': '서비스',
            'Platform': '플랫폼',
            'System': '시스템',
            'Data': '데이터',
            'Cloud': '클라우드',
            'Mobile': '모바일',
            'Web': '웹',
            'App': '앱',
            'Software': '소프트웨어',
            'Hardware': '하드웨어',
            'Network': '네트워크',
            'Server': '서버',
            'Client': '클라이언트',
            'Database': '데이터베이스',
            'Framework': '프레임워크',
            'Library': '라이브러리',
            'Module': '모듈',
            'Package': '패키지',

            # 일본어 (히라가나/가타카나)
            'ありがとう': '아리가토',
            'こんにちは': '곤니치와',
            'さようなら': '사요나라',
            'すみません': '스미마셍',
            'おはよう': '오하요',
            'カタカナ': '카타카나',
            'ひらがな': '히라가나',

            # 중국어 (간체/번체)
            '你好': '니하오',
            '谢谢': '시에시에',
            '再见': '짜이찌엔',
            '对不起': '뚜이부치',
        }

        # 대소문자 무시를 위한 소문자 키 매핑
        self.lowercase_dict = {k.lower(): v for k, v in self.dictionary.items()}

    def get_pronunciation(self, word: str) -> str:
        """
        단어의 한글 발음 반환

        Args:
            word: 원본 단어 (영어, 일본어, 중국어 등)

        Returns:
            한글 발음 (사전에 없으면 원본 반환)
        """
        # 대소문자 무시 검색
        return self.lowercase_dict.get(word.lower(), word)

    def has_pronunciation(self, word: str) -> bool:
        """단어가 사전에 있는지 확인"""
        return word.lower() in self.lowercase_dict

    def add_word(self, word: str, pronunciation: str):
        """사전에 새 단어 추가"""
        self.dictionary[word] = pronunciation
        self.lowercase_dict[word.lower()] = pronunciation

    def load_from_file(self, file_path: str):
        """외부 파일에서 사전 로드 (JSON)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                custom_dict = json.load(f)
                self.dictionary.update(custom_dict)
                self.lowercase_dict = {k.lower(): v for k, v in self.dictionary.items()}
                print(f"✅ 발음 사전 로드 완료: {len(custom_dict)}개 단어")
        except Exception as e:
            print(f"⚠️ 발음 사전 로드 실패: {e}")

    def save_to_file(self, file_path: str):
        """현재 사전을 파일로 저장"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.dictionary, f, ensure_ascii=False, indent=2)
            print(f"✅ 발음 사전 저장 완료: {file_path}")
        except Exception as e:
            print(f"⚠️ 발음 사전 저장 실패: {e}")
