# myapp/views.py
import os
import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@csrf_exempt  # 为了方便测试，暂时禁用CSRF保护，生产环境应考虑更安全的方式
@require_http_methods(["GET", "POST"])  # 限制只允许GET和POST方法
def recruitment_criteria_api(request):
    # 构建JSON文件的绝对路径
    # 文件位于app的migrations目录下
    file_path = os.path.join(os.path.dirname(__file__), 'migrations', 'recruitment_criteria.json')

    if request.method == 'GET':
        # 处理GET请求：读取文件并返回内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return JsonResponse({'code': 200, 'message': '成功', 'data': data})
        except FileNotFoundError:
            print("文件不存在")
            return JsonResponse({'code': 404, 'message': '文件不存在'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'code': 500, 'message': '文件格式错误，非有效JSON'}, status=500)
        except Exception as e:
            return JsonResponse({'code': 500, 'message': f'服务器内部错误: {str(e)}'}, status=500)

    elif request.method == 'POST':
        # 处理POST请求：修改文件内容
        try:
            # 解析POST请求中的JSON数据
            new_data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'code': 400, 'message': '请求体中包含无效的JSON数据'}, status=400)

        # 在这里可以添加对new_data的具体验证逻辑
        # if not validate_new_data(new_data):
        #     return JsonResponse({'code': 400, 'message': '提交的数据格式或内容不符合要求'}, status=400)

        try:
            # 将新数据写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, indent=4, ensure_ascii=False)  # indent使JSON格式化，便于阅读
            return JsonResponse({'code': 200, 'message': '文件更新成功'})
        except Exception as e:
            return JsonResponse({'code': 500, 'message': f'写入文件时发生错误: {str(e)}'}, status=500)