from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
from datetime import datetime
import os
import logging
import random
from logging.handlers import RotatingFileHandler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class TweetMonitor:
    def __init__(self):
        # 添加首次运行标志
        self.first_run = True
        
        # 首先设置日志
        self.setup_logging()
        
        # 然后加载配置文件
        try:
            self.load_config()
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            raise
        
        # 设置Chrome选项
        self.setup_chrome_options()
        
        # 从配置文件加载账号
        self.config_file = 'twitter_accounts.json'
        self.load_accounts()
        
        # 添加配置文件最后修改时间
        self.last_config_modified = os.path.getmtime(self.config_file) if os.path.exists(self.config_file) else 0
        
        # 创建数据保存目录
        self.base_data_dir = "tweets_data"
        for username in self.accounts.keys():
            user_dir = os.path.join(self.base_data_dir, username)
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)
        
        self.driver = None
    
    def setup_logging(self):
        """设置日志"""
        log_file = 'twitter_monitor.log'
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        self.logger = logging.getLogger('TwitterMonitor')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def setup_chrome_options(self):
        """设置Chrome选项"""
        self.chrome_options = Options()
        # self.chrome_options.add_argument('--headless')  # 调试时注释掉这行
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--start-maximized')
        
        # 添加更多选项来绕过检测
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_argument('--ignore-certificate-errors')
        self.chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 添加用户代理
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 添加窗口大小
        self.chrome_options.add_argument('--window-size=1920,1080')
        
        # 禁用 JavaScript 错误
        self.chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    def load_accounts(self):
        """从配置文件加载账号"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.accounts = json.load(f)
                self.logger.info(f"已加载 {len(self.accounts)} 个账号")
            else:
                # 创建默认配置
                self.accounts = {
                    'elonmusk': {
                        'name': 'Elon Musk',
                        'username': 'elonmusk',
                        'last_tweet_id': None,
                        'enabled': True
                    }
                }
                self.save_accounts()
        except Exception as e:
            self.logger.error(f"加载账号配置时出错: {e}")
            self.accounts = {}
    
    def save_accounts(self):
        """保存账号配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.accounts, f, indent=4, ensure_ascii=False)
            self.logger.info("账号配置已保存")
        except Exception as e:
            self.logger.error(f"保存账号配置时出错: {e}")
    
    def check_config_updates(self):
        """检查配置文件是否有更新"""
        try:
            if os.path.exists(self.config_file):
                current_mtime = os.path.getmtime(self.config_file)
                if current_mtime > self.last_config_modified:
                    self.logger.info("检测到配置文件更新，重新加载账号...")
                    self.load_accounts()
                    self.last_config_modified = current_mtime
                    
                    # 为新账号创建数据目录
                    for username in self.accounts.keys():
                        user_dir = os.path.join(self.base_data_dir, username)
                        if not os.path.exists(user_dir):
                            os.makedirs(user_dir)
        except Exception as e:
            self.logger.error(f"检查配置更新时出错: {e}")
    def init_driver(self):
        """初始化浏览器"""
        try:
            if self.driver is not None:
                self.driver.quit()
            
            # 修改 ChromeDriver 的安装方式
            chrome_options = self.chrome_options
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # 使用系统已安装的 ChromeDriver
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
            except:
                # 如果系统未安装，则尝试自动下载安装
                service = Service(ChromeDriverManager(cache_valid_range=1).install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            return True
        except Exception as e:
            self.logger.error(f"初始化浏览器失败: {e}")
            return False
    
    def follow_accounts(self):
        """自动关注配置文件中的账号"""
        try:
            self.logger.info("开始关注配置的账号...")
            for username, account_info in self.accounts.items():
                if not account_info.get('enabled', True):
                    continue
                    
                try:
                    # 访问用户主页
                    self.driver.get(f"https://twitter.com/{username}")
                    time.sleep(8)  # 增加页面加载等待时间
                    
                    # 尝试滚动页面以确保内容加载
                    self.driver.execute_script("window.scrollBy(0, 300)")
                    time.sleep(2)
                    
                    # 更新关注按钮的选择器
                    follow_button = None
                    selectors = [
                        '[data-testid="followButton"]',
                        '[data-testid="follow"]',
                        '[aria-label*="关注"]',
                        '[aria-label*="Follow"]',
                        'div[role="button"]:has-text("关注")',
                        'div[role="button"]:has-text("Follow")',
                        '//div[@role="button"][contains(., "关注")]',
                        '//div[@role="button"][contains(., "Follow")]'
                    ]
                    
                    for selector in selectors:
                        try:
                            if selector.startswith('//'):
                                # 使用 XPath 选择器
                                follow_button = WebDriverWait(self.driver, 10).until(
                                    EC.presence_of_element_located((By.XPATH, selector))
                                )
                            else:
                                # 使用 CSS 选择器
                                follow_button = WebDriverWait(self.driver, 10).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                                )
                            if follow_button and follow_button.is_displayed():
                                break
                        except:
                            continue
                    
                    if not follow_button:
                        self.logger.warning(f"未找到 @{username} 的关注按钮")
                        continue
                    
                    # 使用 JavaScript 点击按钮
                    self.driver.execute_script("arguments[0].click();", follow_button)
                    self.logger.info(f"已关注用户 @{username}")
                    time.sleep(random.randint(4, 8))
                    
                except Exception as e:
                    self.logger.error(f"关注用户 @{username} 时出错: {str(e)}")
                    continue
                
        except Exception as e:
            self.logger.error(f"执行自动关注功能时出错: {str(e)}")
    
    def login_twitter(self):
        """登录Twitter"""
        try:
            self.logger.info("正在登录Twitter...")
            self.driver.get("https://twitter.com/login")
            time.sleep(5)
            
            # 输入邮箱
            email_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]'))
            )
            email_input.send_keys(self.twitter_email)
            email_input.send_keys(Keys.RETURN)
            time.sleep(3)
            
            # 如果要求输入用户名（注意：更新了选择器）
            try:
                username_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@data-testid='ocfEnterTextTextInput']"))
                )
                # 移除 @ 符号，因为输入框不需要
                clean_username = self.twitter_username.replace('@', '')
                username_input.send_keys(clean_username)
                username_input.send_keys(Keys.RETURN)
                time.sleep(3)
            except Exception as e:
                self.logger.info(f"无需输入用户名，继续下一步: {e}")
                
            # 输入密码
            password_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="password"]'))
            )
            password_input.send_keys(self.twitter_password)
            password_input.send_keys(Keys.RETURN)
            time.sleep(5)
            
            return True
            
        except Exception as e:
            self.logger.error(f"登录Twitter失败: {e}")
            return False
    
    def save_tweet(self, tweet_data):
        """保存推文"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            username = tweet_data['username']
            filename = os.path.join(self.base_data_dir, username, f"tweet_{timestamp}.json")
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(tweet_data, f, ensure_ascii=False, indent=4)
            
            self.logger.info(f"已保存{username}的推文到 {filename}")
            
        except Exception as e:
            self.logger.error(f"保存推文时出错: {e}")
    
    def cleanup(self):
        """清理资源"""
        self.logger.info("执行清理操作...")
        if self.driver is not None:
            self.driver.quit()
        self.init_driver()
        self.login_twitter()
    
    def monitor(self, interval=60):
        """监控多个账号的推文"""
        cleanup_counter = 0
        
        while True:
            try:
                # 检查配置文件是否有更新
                self.check_config_updates()
                
                if not hasattr(self, 'driver') or self.driver is None:
                    if not self.init_driver() or not self.login_twitter():
                        time.sleep(60)
                        continue
                
                # 只在首次运行时执行关注操作
                if self.first_run:
                    self.follow_accounts()
                    self.first_run = False
                
                cleanup_counter += 1
                if cleanup_counter >= 100:
                    self.cleanup()
                    cleanup_counter = 0
                
                # 遍历所有启用的账号
                for username, account_info in self.accounts.items():
                    # 检查账号是否启用
                    if not account_info.get('enabled', True):
                        continue
                        
                    self.logger.info(f"\n正在检查 {account_info['name']} (@{username}) 的推文...")
                    
                    tweets = self.get_tweets(username)
                    
                    if tweets:
                        newest_tweet = tweets[0]
                        
                        if account_info['last_tweet_id'] != newest_tweet['id']:
                            self.logger.info(f"\n检测到 {account_info['name']} 的新推文!")
                            self.logger.info(f"时间: {newest_tweet['created_at']}")
                            self.logger.info(f"内容: {newest_tweet['text']}")
                            self.logger.info(f"点赞: {newest_tweet['likes']}")
                            self.logger.info(f"转发: {newest_tweet['retweets']}")
                            
                            self.save_tweet(newest_tweet)
                            # 发送邮件通知
                            self.send_email_notification(newest_tweet)
                            account_info['last_tweet_id'] = newest_tweet['id']
                            # 保存最新的 tweet_id 到配置文件
                            self.save_accounts()
                    
                    time.sleep(random.randint(3, 8))
                
                random_delay = interval + random.randint(-10, 10)
                self.logger.info(f"下次检查将在 {random_delay} 秒后")
                time.sleep(random_delay)
                
            except KeyboardInterrupt:
                self.logger.info("收到停止信号，正在停止监控...")
                break
            except Exception as e:
                self.logger.error(f"监控过程中出错: {e}")
                if hasattr(self, 'driver'):
                    self.driver.quit()
                self.driver = None
                time.sleep(60)
    
    def get_tweets(self, username):
        """获取指定用户的推文"""
        try:
            # 访问用户主页
            self.driver.get(f"https://twitter.com/{username}")
            time.sleep(5)
            
            # 等待推文加载
            tweets = WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'article[data-testid="tweet"]'))
            )
            
            tweets_data = []
            for tweet in tweets[:5]:  # 只获取最新的5条推文
                try:
                    # 获取推文ID
                    tweet_link = tweet.find_element(By.CSS_SELECTOR, 'a[href*="/status/"]').get_attribute('href')
                    tweet_id = tweet_link.split('/status/')[1].split('?')[0]
                    
                    # 获取推文文本
                    text_element = tweet.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetText"]')
                    text = text_element.text
                    
                    # 获取时间
                    time_element = tweet.find_element(By.CSS_SELECTOR, 'time')
                    created_at = time_element.get_attribute('datetime')
                    
                    # 更新获取互动数据的选择器
                    try:
                        likes = tweet.find_element(By.CSS_SELECTOR, '[data-testid="like"] span span').text
                    except:
                        likes = '0'
                        
                    try:
                        retweets = tweet.find_element(By.CSS_SELECTOR, '[data-testid="retweet"] span span').text
                    except:
                        retweets = '0'
                    
                    # 处理空字符串和数字格式化
                    likes = '0' if not likes else likes.replace(',', '')
                    retweets = '0' if not retweets else retweets.replace(',', '')
                    
                    tweet_data = {
                        'id': tweet_id,
                        'username': username,
                        'text': text,
                        'created_at': created_at,
                        'likes': likes,
                        'retweets': retweets
                    }
                    
                    tweets_data.append(tweet_data)
                    
                except Exception as e:
                    self.logger.error(f"解析推文时出错: {e}")
                    continue
            
            return tweets_data
            
        except Exception as e:
            self.logger.error(f"获取推文失败: {e}")
            return None
    
    def load_config(self):
        """加载配置文件"""
        try:
            config_file = 'config.json'
            if not os.path.exists(config_file):
                self.logger.error("配置文件不存在，请创建 config.json 文件")
                raise FileNotFoundError("配置文件不存在")
                
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 获取 Twitter 登录凭证
            credentials = config.get('twitter_credentials', {})
            self.twitter_email = credentials.get('email')
            self.twitter_username = credentials.get('username')
            self.twitter_password = credentials.get('password')
            
            # 获取邮件设置
            email_settings = config.get('email_settings', {})
            self.smtp_server = email_settings.get('smtp_server')
            self.smtp_port = email_settings.get('smtp_port')
            self.sender_email = email_settings.get('sender_email')
            self.sender_password = email_settings.get('sender_password')
            self.email_recipients = email_settings.get('recipients', [])
            
            # 验证必要的配置是否存在
            if not all([self.twitter_email, self.twitter_username, self.twitter_password]):
                raise ValueError("Twitter 登录凭证不完整")
            if not all([self.smtp_server, self.smtp_port, self.sender_email, 
                       self.sender_password, self.email_recipients]):
                raise ValueError("邮件配置不完整")
                
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            raise

    def send_email_notification(self, tweet_data):
        """发送邮件通知"""
        try:
            # 创建邮件内容
            subject = f"新推文通知 - 来自 {tweet_data['username']}"
            body = f"""
检测到新推文！

用户: {tweet_data['username']}
时间: {tweet_data['created_at']}
内容: {tweet_data['text']}
点赞: {tweet_data['likes']}
转发: {tweet_data['retweets']}

推文链接: https://twitter.com/{tweet_data['username']}/status/{tweet_data['id']}
            """
            
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 连接到SMTP服务器
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            
            # 发送给所有接收者
            for recipient in self.email_recipients:
                msg['To'] = recipient
                server.send_message(msg)
                self.logger.info(f"已发送邮件通知到 {recipient}")
            
            server.quit()
            
        except Exception as e:
            self.logger.error(f"发送邮件通知失败: {e}")

def main():
    monitor = TweetMonitor()
    monitor.monitor(interval=60)  # 可以调整检查间隔

if __name__ == "__main__":
    main()