import json
import pika
from flask import Flask
import threading
from SentimentAnalysis import SentimentAnalysis
import logging

# 配置日志
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Flask 应用初始化
app = Flask(__name__)
sentimentClassifier = SentimentAnalysis()

# 全局 RabbitMQ 连接和 Channel
rabbitmq_connection = None
publish_channel = None

# RabbitMQ 配置信息
RABBITMQ_HOST = '122.51.221.6'
QUEUE_NAME = 'record.queue'
EXCHANGE_NAME = "record.exchange"
ROUTING_KEY = "record.routingkey"
RABBITMQ_PORT = 30272
VIRTUAL_HOST = "md"
PRODUCE_RABBITMQ_NAME = "callback.queue"

data = None


def load_data():
    global data
    with open('Mood_relate_file.json', 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    data = {}
    for emotion in raw_data['emotions']:
        key = emotion['name'].lower()
        data[key] = emotion
load_data()


def CheckUpContent(emotion):
    emotion_lower = emotion.lower()
    if emotion_lower in data:
        emotion_data = data[emotion_lower]
        return emotion_data['name'], emotion_data['comforting_language'][0], emotion_data['behavioral_guidance']
    return None


# 封装消息并返回结果
def organizePub(response):
    result = dict()
    result["record_Id"] = response.get('record_Id', 'unknown')
    result['data'] = response.get('data', [])
    result['top_emotion'] = response.get('top_emotion', {})
    result['comfort_language'] = response.get('comfort_language', {})
    result['behavioral_guidance'] = response.get('behavioral_guidance', {})
    return json.dumps(result)


# 消费 RabbitMQ 消息的回调函数
def callback(ch, method, properties, body):
    message = json.loads(body)
    logging.info(f"Received message: {message}")
    record_Id = message.get('recordId')
    text = message.get('content')
    text_list = [text]
    response = sentimentClassifier.sentimentAnalze(text_list)
    top_emotion, comfort_language, behavioral_guidance = CheckUpContent(response[0][0]['label'])
    send_message = {
        "record_Id": record_Id,
        "data": response,
        'top_emotion': top_emotion,
        'comfort_language': comfort_language,
        'behavioral_guidance': behavioral_guidance
    }

    # 发布消息到另一个队列
    send_to_queue(send_message)


# 发布消息到 RabbitMQ
def send_to_queue(message):
    global publish_channel
    if publish_channel:
        send_message = organizePub(message)
        publish_channel.basic_publish(
            exchange='',
            routing_key=PRODUCE_RABBITMQ_NAME,
            body=send_message
        )
        logging.info(f"Sent message to {PRODUCE_RABBITMQ_NAME}: {send_message}")
    else:
        logging.error("Publish channel is not initialized")


# 启动 RabbitMQ 消费者
def start_consuming():
    global rabbitmq_connection, publish_channel
    try:
        # 设置连接参数
        credentials = pika.PlainCredentials("md", "123")
        rabbitmq_connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials,
                                      virtual_host=VIRTUAL_HOST)
        )
        logging.info("Successfully connected to RabbitMQ")

        # 创建消费和发布的 Channel
        consume_channel = rabbitmq_connection.channel()
        publish_channel = rabbitmq_connection.channel()

        # 声明交换机和队列
        consume_channel.exchange_declare(exchange=EXCHANGE_NAME)
        consume_channel.queue_declare(queue=QUEUE_NAME, durable=True)
        publish_channel.queue_declare(queue=PRODUCE_RABBITMQ_NAME, durable=True)

        consume_channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key=ROUTING_KEY)

        # 设置消费者回调函数
        consume_channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=True)

        logging.info('Waiting for messages. To exit press CTRL+C')

        # 开始消费
        consume_channel.start_consuming()

    except pika.exceptions.AMQPConnectionError as e:
        logging.error(f"Failed to connect to RabbitMQ: {e}")
    except Exception as e:
        logging.error(f"Error during RabbitMQ consumption: {e}")


# Flask 路由
@app.route("/")
def index():
    return "Hello World!"


start_consuming()
app.run(debug=False, use_reloader=False)
