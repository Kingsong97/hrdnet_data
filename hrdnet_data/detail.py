import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

# Selenium 설정
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # 브라우저를 표시하지 않음
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# 데이터 폴더 경로
data_folder = 'hrdnet_data'
years = ['2024']
regions = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주']

for year in years:
    for region in regions:
        # 목록 데이터를 JSON 파일에서 불러오기
        file_path = os.path.join(data_folder, f'hrdnet_data_{year}_{region}.json')
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue

        with open(file_path, 'r', encoding='utf-8') as json_file:
            list_data = json.load(json_file)['data']

        detailed_data = []
        total_items = len(list_data)

        for index, item in enumerate(list_data, start=1):
            try:
                # 상세 페이지 URL 동적으로 생성
                tracseId = item['trprId']
                tracseTme = item['trprDegr']
                crseTracseSe = item['trainTargetCd']
                trainstCstmrId = item['trainstCstId']
                url = f'https://www.hrd.go.kr/hrdp/co/pcobo/PCOBO0100P.do?tracseId={tracseId}&tracseTme={tracseTme}&crseTracseSe={crseTracseSe}&trainstCstmrId={trainstCstmrId}#undefined'
                driver.get(url)

                # 특정 요소가 로드될 때까지 대기
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//li[@aria-controls='section1-1']/button"))
                )

                # 각 탭 클릭 및 내용 가져오기
                tabs = [
                    ('section1-1', 'training_overview'),
                    ('section1-2', 'related_certificates'),
                    ('section1-4', 'satisfaction_reviews'),
                    ('section1-5', 'training_inquiries'),
                    ('section1-7', 'other_course_info')
                ]
                detail = item.copy()
                data_dict = {}

                for section_id, tab_key in tabs:
                    try:
                        # 탭 클릭
                        tab_element = driver.find_element(By.XPATH, f"//li[@aria-controls='{section_id}']/button")
                        tab_element.click()
                        
                        # 탭 콘텐츠가 로드될 때까지 대기
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.ID, section_id))
                        )
                        
                        # 현재 페이지 소스 가져오기
                        page_source = driver.page_source

                        # BeautifulSoup을 사용하여 HTML 파싱
                        soup = BeautifulSoup(page_source, 'html.parser')
                        section_content = soup.find(id=section_id)

                        if section_content:
                            if section_id == 'section1-4':
                                # section1-4의 수강후기 데이터 추출
                                reviews = []
                                review_areas = section_content.find_all('div', class_='commentReviewArea')
                                for review_div in review_areas:
                                    review_parts = review_div.find_all('dd', class_='body')
                                    for part in review_parts:
                                        ment = part.find('p', class_='ment')
                                        if ment:
                                            reviews.append({"ment": ment.get_text(strip=True)})
                                data_dict[tab_key] = reviews
                            elif section_id == 'section1-5':
                                # section1-5의 문의 데이터 추출
                                inquiries = []
                                comment_boxes = section_content.find_all('div', class_='commentBox')
                                for comment_div in comment_boxes:
                                    inquiry = comment_div.get_text(strip=True)
                                    inquiries.append(inquiry)
                                data_dict[tab_key] = inquiries
                            else:
                                # 일반적인 테이블 데이터 추출
                                tables = section_content.find_all('table')
                                tables_data = []
                                for table in tables:
                                    headers = [header.get_text(strip=True) for header in table.find_all('th')]
                                    rows = []
                                    for row in table.find_all('tr'):
                                        cells = row.find_all('td')
                                        if len(cells) > 0:
                                            row_data = [cell.get_text(strip=True) for cell in cells]
                                            rows.append(row_data)
                                    tables_data.append({'headers': headers, 'rows': rows})
                                data_dict[tab_key] = tables_data
                        else:
                            data_dict[tab_key] = []
                    except Exception as e:
                        print(f"Failed to retrieve data for tab {tab_key}: {e}")
                        data_dict[tab_key] = []

                detail['details'] = data_dict
                detailed_data.append(detail)

                # 진행 상태 출력
                print(f"Progress for {year} {region}: {index}/{total_items} completed")
            
            except Exception as e:
                print(f"Failed to process item {index} in {region}, {year}: {e}")

        # 연도별, 지역별 상세 데이터 JSON 파일로 저장
        detailed_file_path = os.path.join(data_folder, f'detailed_webpage_data_{year}_{region}.json')
        try:
            with open(detailed_file_path, 'w', encoding='utf-8') as json_file:
                json.dump(detailed_data, json_file, ensure_ascii=False, indent=4)
            print(f"Detailed data for year {year}, region {region} has been successfully saved to {detailed_file_path}")
        except Exception as e:
            print(f"Failed to save JSON file for {year}, {region}: {e}")

# 드라이버 종료
driver.quit()
