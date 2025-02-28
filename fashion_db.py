import sqlite3
import os
import json
from datetime import datetime

class FashionDB:
    def __init__(self, db_path="fashion_ai.db"):
        """데이터베이스 초기화"""
        self.db_path = db_path
        self.conn = None
        self.create_tables()
        
    def _connect(self):
        """데이터베이스 연결"""
        try:
            print(f"DB 연결 시도: {self.db_path}")
            self.conn = sqlite3.connect(self.db_path)
            print("DB 연결 성공!")
            return self.conn.cursor()
        except sqlite3.Error as e:
            print(f"DB 연결 오류: {e}")
            raise
    
    def _close(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            self.conn.commit()
            self.conn.close()
            self.conn = None
    
    def create_tables(self):
        """필요한 테이블 생성"""
        try:
            cursor = self._connect()
            
            # 태그 테이블 생성
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT,
                image_name TEXT,
                tags TEXT,
                created_at TEXT
            )
            ''')
            
            # 코디 테이블 생성
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS outfits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                style TEXT,
                season TEXT, 
                base_color TEXT,
                outfit_json TEXT,
                created_at TEXT
            )
            ''')
            
            # 크롤링 결과 테이블 생성
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS crawled_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                image_path TEXT,
                source_url TEXT,
                source_site TEXT,
                tags TEXT,
                created_at TEXT
            )
            ''')
            
            self._close()
        except Exception as e:
            print(f"테이블 생성 실패: {e}")
    
    def save_tags(self, image_path, tags):
        """태그 저장"""
        try:
            cursor = self._connect()
            image_name = os.path.basename(image_path)
            tags_json = json.dumps(tags, ensure_ascii=False)
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                'INSERT INTO tags (image_path, image_name, tags, created_at) VALUES (?, ?, ?, ?)',
                (image_path, image_name, tags_json, created_at)
            )
            
            last_id = cursor.lastrowid
            self._close()
            return last_id
        except Exception as e:
            print(f"태그 저장 실패: {e}")
            if self.conn:
                self._close()
            return None
    
    def get_all_tags(self):
        """모든 태그 조회"""
        try:
            cursor = self._connect()
            cursor.execute('SELECT * FROM tags ORDER BY created_at DESC')
            rows = cursor.fetchall()
            self._close()
            return rows
        except Exception as e:
            print(f"태그 조회 실패: {e}")
            if self.conn:
                self._close()
            return []
    
    def save_outfit(self, style, season, base_color, outfit_data):
        """코디 저장"""
        try:
            cursor = self._connect()
            outfit_json = json.dumps(outfit_data, ensure_ascii=False)
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                'INSERT INTO outfits (style, season, base_color, outfit_json, created_at) VALUES (?, ?, ?, ?, ?)',
                (style, season, base_color, outfit_json, created_at)
            )
            
            last_id = cursor.lastrowid
            self._close()
            return last_id
        except Exception as e:
            print(f"코디 저장 실패: {e}")
            if self.conn:
                self._close()
            return None
    
    def get_all_outfits(self):
        """모든 코디 조회"""
        try:
            cursor = self._connect()
            cursor.execute('SELECT * FROM outfits ORDER BY created_at DESC')
            rows = cursor.fetchall()
            self._close()
            return rows
        except Exception as e:
            print(f"코디 조회 실패: {e}")
            if self.conn:
                self._close()
            return []
    
    def save_crawled_item(self, name, image_path, source_url, source_site, tags=None):
        """크롤링 결과 저장"""
        try:
            cursor = self._connect()
            tags_json = json.dumps(tags, ensure_ascii=False) if tags else None
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                'INSERT INTO crawled_items (name, image_path, source_url, source_site, tags, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (name, image_path, source_url, source_site, tags_json, created_at)
            )
            
            last_id = cursor.lastrowid
            self._close()
            return last_id
        except Exception as e:
            print(f"크롤링 결과 저장 실패: {e}")
            if self.conn:
                self._close()
            return None
    
    def get_crawled_items(self, source_site=None, limit=50):
        """크롤링 결과 조회"""
        try:
            cursor = self._connect()
            if source_site:
                cursor.execute('SELECT * FROM crawled_items WHERE source_site = ? ORDER BY created_at DESC LIMIT ?',
                            (source_site, limit))
            else:
                cursor.execute('SELECT * FROM crawled_items ORDER BY created_at DESC LIMIT ?', (limit,))
            rows = cursor.fetchall()
            self._close()
            return rows
        except Exception as e:
            print(f"크롤링 결과 조회 실패: {e}")
            if self.conn:
                self._close()
            return []

    def search_items_by_tag(self, tag, limit=50):
        """태그로 아이템 검색"""
        try:
            cursor = self._connect()
            # JSON에서 태그 검색을 위한 LIKE 패턴
            pattern = f"%{tag}%"
            cursor.execute('''
                SELECT * FROM crawled_items 
                WHERE tags LIKE ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (pattern, limit))
            rows = cursor.fetchall()
            self._close()
            return rows
        except Exception as e:
            print(f"태그 검색 실패: {e}")
            if self.conn:
                self._close()
            return []

    def recommend_items(self, category=None, style=None, color=None, limit=5):
        """조건에 맞는 아이템 추천"""
        try:
            cursor = self._connect()
            query = 'SELECT * FROM crawled_items WHERE 1=1 '
            params = []
            
            if category:
                query += 'AND tags LIKE ? '
                params.append(f"%{category}%")
            
            if style:
                query += 'AND tags LIKE ? '
                params.append(f"%{style}%")
            
            if color:
                query += 'AND tags LIKE ? '
                params.append(f"%{color}%")
                
            query += 'ORDER BY RANDOM() LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            self._close()
            return rows
        except Exception as e:
            print(f"아이템 추천 실패: {e}")
            if self.conn:
                self._close()
            return []

    def get_tags_statistics(self):
        """저장된 태그 통계 정보"""
        try:
            cursor = self._connect()
            cursor.execute("SELECT tags FROM crawled_items")
            all_tag_lists = cursor.fetchall()
            self._close()
            
            # 태그 빈도 분석
            tag_count = {}
            for tag_list_tuple in all_tag_lists:
                if tag_list_tuple[0]:  # None이 아니면
                    try:
                        tags = json.loads(tag_list_tuple[0])
                        for tag in tags:
                            tag_count[tag] = tag_count.get(tag, 0) + 1
                    except:
                        pass
                        
            # 빈도순 정렬
            sorted_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)
            return sorted_tags
        except Exception as e:
            print(f"태그 통계 분석 실패: {e}")
            if self.conn:
                self._close()
            return []

if __name__ == "__main__":
    # 테스트를 위한 코드
    print("FashionDB 테스트 시작...")
    
    import os
    print(f"현재 작업 디렉토리: {os.getcwd()}")
    
    # DB 파일 경로 확인
    db_path = "fashion_ai.db"
    print(f"DB 파일 경로: {os.path.abspath(db_path)}")
    
    if os.path.exists(db_path):
        print(f"DB 파일이 존재합니다. 크기: {os.path.getsize(db_path)} 바이트")
    else:
        print("DB 파일이 존재하지 않습니다. 새로 생성될 예정입니다.")
    
    try:
        # DB 인스턴스 생성
        db = FashionDB()
        print("\nDB 인스턴스 생성 완료")
        
        # 테스트 태그 저장
        test_id = db.save_tags("test_image.jpg", ["테스트", "태그"])
        print(f"테스트 태그 저장 ID: {test_id}")
        
        # 테스트 태그 조회
        tags = db.get_all_tags()
        print(f"저장된 태그 수: {len(tags)}")
        if tags:
            print(f"마지막 저장된 태그: {tags[0]}")
        
        print("\nFashionDB 테스트 완료!")
    except Exception as e:
        print(f"\nDB 테스트 실패: {e}")