import json
from flask import Flask, jsonify, request
from flask_restful import Resource, Api
from SentimentAnalysis import SentimentAnalysis as SentimentTool  # 确保导入正确

data = None

def load_data():
    global data
    with open('Mood_relate_file.json', 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    data = {emotion['name'].lower(): emotion for emotion in raw_data['emotions']}

load_data()
app = Flask(__name__)
api = Api(app)
sentiment_tool = SentimentTool()

def CheckUpContent(emotion):
    emotion_lower = emotion.lower()
    if emotion_lower in data:
        emotion_data = data[emotion_lower]
        return emotion_data['name'], emotion_data['comforting_language'][0], emotion_data['behavioral_guidance']
    return None, None, None

class SentimentAnalysisResource(Resource):
    def post(self):
        content = request.json.get('content')
        if not content:
            return {"error": "Missing content parameter"}, 400

        result = sentiment_tool.sentimentAnalze(content)
        top_emotion, comfort_language, behavioral_guidance = CheckUpContent(result[0][0]['label'])

        if top_emotion is None:
            return {"error": "Emotion not found"}, 404

        dic_result = {
            'data': result,
            'topEmotion': top_emotion,
            'comfortLanguage': comfort_language,
            'behavioralGuidance': behavioral_guidance
        }
        return dic_result, 200

# 添加路由
api.add_resource(SentimentAnalysisResource, '/sentimentAnalysis')

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000)
