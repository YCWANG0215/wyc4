from flask import jsonify
from flask import Flask
from flask import render_template
from flask import request
import csv
import json
import os
import sys
import uuid

from azure.core.exceptions import AzureError
from azure.cosmos import CosmosClient, PartitionKey
from collections import Counter

app = Flask(__name__)

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/')
def hello_world():  # put application's code here
    return render_template('index.html')

@app.route('/api/mydata', methods=['GET'])
def api_mydata():
    data = get_data()
    return jsonify(data)


@app.route('/city/<name>')
def city(name):
    # with open('/Users/wyc/Desktop/assignment1-1/static/us-cities.csv', 'r') as f:
    with open('static/us-cities.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['city'] == name:
                return render_template('city.html', **row)
        return "City not found", 404

def get_data():
    data = []
    # with open('/Users/wyc/Desktop/assignment1-1/static/amazon-reviews.csv', 'r') as f:
    with open('static/amazon-reviews.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data

# update the connection string to your own string
# the database in the tutorial has been deleted.
DB_CONN_STR = "AccountEndpoint=https://wyc.documents.azure.com:443/;AccountKey=aiSuIx1L456T9couzy9P5B8DcM6FIc6oH2PzaNEmpMtCI7XV3Eclc5Oy0NQoae70892IoNRU3WJWACDbPLGLkg=="
db_client_us_cities = CosmosClient.from_connection_string(conn_str = DB_CONN_STR)
# AccountEndpoint = "https://wyc.documents.azure.com:443/"
# AccountKey = "aiSuIx1L456T9couzy9P5B8DcM6FIc6oH2PzaNEmpMtCI7XV3Eclc5Oy0NQoae70892IoNRU3WJWACDbPLGLkg=="
# db_client = CosmosClient(AccountEndpoint, AccountKey)
database_us_cities = db_client_us_cities.get_database_client("us-cities")
container_us_cities = database_us_cities.get_container_client("us-cities")

db_client_amazon_reviews = CosmosClient.from_connection_string(conn_str = DB_CONN_STR)
# AccountEndpoint = "https://wyc.documents.azure.com:443/"
# AccountKey = "aiSuIx1L456T9couzy9P5B8DcM6FIc6oH2PzaNEmpMtCI7XV3Eclc5Oy0NQoae70892IoNRU3WJWACDbPLGLkg=="
# db_client = CosmosClient(AccountEndpoint, AccountKey)
database_amazon_reviews = db_client_amazon_reviews.get_database_client("amazon-reviews")
container_amazon_reviews = database_amazon_reviews.get_container_client("amazon-reviews")
# ctn = list(database.list_containers())
# print(f"containers: {ctn}")

def fetch_data(city_name = None, include_header = False, exact_match = False):
    # db_name = "us-cities"
    # container_name = ""
    # database = db_client.get_database_client(db_name)
    # ctn = list(database.list_containers())
    # print(f"containers: {ctn}")
    QUERY = "SELECT * from c"
    params = None
    if city_name is not None:
        # QUERY = "SELECT * FROM us_cities p WHERE p.city = @city_name"
        QUERY = "SELECT * FROM c where c.city = @city_name"
        params = [dict(name="@city_name", value=city_name)]
        if not exact_match:
            # QUERY = "SELECT * FROM us_cities p WHERE p.city like @city_name"
            QUERY = "SELECT * FROM c WHERE CONTAINS(c.city, @city_name)"
    
    headers = ["city", "lat", "lng", "country", "state", "population"]
    result = []
    row_id = 0
    if include_header:
        line = [x for x in headers]
        line.insert(0, "")
        result.append(line)
    
    for item in container_us_cities.query_items(
        # query=QUERY, parameters=params, enable_cross_partition_query=True,
        query=QUERY, parameters=[dict(name="@city_name", value=city_name)],
        enable_cross_partition_query=True,
    ):
        row_id += 1
        line = [str(row_id)]
        for col in headers:
            line.append(item[col])
        result.append(line)
    return result

# @app.route('/popular_words', methods=['GET'])
# def popular_words():
#     city_name = request.args.get('city')
#     limit = int(request.args.get('limit', default=10))

#     # 查询 Amazon 数据库中指定城市的 review 列
#     query = f"SELECT c.review FROM c JOIN d IN {database_us_cities.id} WHERE d.city = '{city_name}'"
#     # items = list(database_amazon_reviews.query_items(query, enable_cross_partition_query=True))
#     items = list(container_amazon_reviews.query_items(query, enable_cross_partition_query=True))

#     word_counts = {}
#     for item in items:
#         review = item.get("review", "")
#         words = review.split()
#         for word in words:
#             word_counts[word] = word_counts.get(word, 0) + 1

#     sorted_words = sorted(word_counts.items(), key=lambda x: min(x[1], 10), reverse=True)
#     response_data = [{"term": word, "popularity": min(count, 10)} for word, count in sorted_words[:limit]]

#     return jsonify(response_data)

def calculate_population(city_name):
    query = f"SELECT c.population FROM c WHERE c.city = '{city_name}'"

    # 查询符合条件的城市人口数据
    items = container_us_cities.query_items(query=query, enable_cross_partition_query=True)

    population = 0
    # 收集城市的人口数据
    for item in items:
        population += int(item.get("population", 0))

    return population

# /popular2 is the answer of 11
@app.route('/popular_words2', methods=['GET'])
def popular_words2():
    city_name = request.args.get('city', default="Burton")
    limit = int(request.args.get('limit', default=10))
    city_population = calculate_population(city_name)

    query = f"SELECT c.review FROM c WHERE c.city = '{city_name}'"
    items = container_amazon_reviews.query_items(query=query, enable_cross_partition_query=True)

    word_counts = {}
    # 分析评论数据，计算每个单词出现的次数
    for item in items:
        review = item.get("review", "")
        words = review.split()  # 假设以空格分割单词
        for word in words:
            if word in word_counts:
                word_counts[word] += 1
            else:
                word_counts[word] = 1

    popular_words = {}
    # 计算出现在三个不同城市评论中的单词的流行度
    for word, count in word_counts.items():
        if count >= 3:
            popular_words[word] = city_population

    # 对结果按照人口总数进行排序
    sorted_words = sorted(popular_words.items(), key=lambda x: x[1], reverse=True)

    # 限制结果数量并构造返回的 JSON 数据
    response_data = [{"term": word, "population": count} for word, count in sorted_words[:limit]]

    return response_data

# /popular_words is the answer of 10
@app.route('/popular_words', methods=['GET'])
def popular_words():
    # 获取查询参数
    city_name = request.args.get('city', default="Burton")
    # city_name = "Burton"
    limit = int(request.args.get('limit', default=10))
    # limit = 10
    
    # query = "SELECT c.review FROM c WHERE c.city = @cityname"
    # query = f"SELECT c.review FROM c WHERE c.city = '{city_name}'"
    query = f"SELECT c.review FROM c WHERE c.city = '{city_name}'" if city_name else "SELECT c.review FROM c"

    ####################
    items = list(container_amazon_reviews.query_items(query=query, enable_cross_partition_query=True))

    word_counts = {}
    for item in items:
        reviews = item.get("review", "").split()  # 假设以空格分割单词
        for word in reviews:
            word_counts[word] = word_counts.get(word, 0) + 1

    # 按流行度排序并限制结果
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    # 构建响应
    response_data = [{"term": word, "popularity": count if count <= 10 else 10} for word, count in sorted_words]
    ####################


    return jsonify(response_data)

@app.route('/substitute_words', methods=['POST'])
def substitute_words():
    req_data = request.get_json()

    word_to_replace = req_data.get('word')
    substitute_word = req_data.get('substitue')

    query = f"SELECT * FROM c WHERE CONTAINS(c.review, '{word_to_replace}')"
    items = list(container_amazon_reviews.query_items(query=query, enable_cross_partition_query=True))

    affected_reviews = 0
    for item in items:
        review = item.get("review", "")
        updated_review = review.replace(word_to_replace, substitute_word)

        # 更新评论
        item['review'] = updated_review
        container_amazon_reviews.replace_item(item=item)
        
        affected_reviews += 1

    return jsonify({'affected_reviews': affected_reviews})



def get_word_counts(city_name):
    # 查询特定城市的评论数据
    query = f"SELECT c.review FROM c WHERE c.city = '{city_name}'"
    items = list(database_amazon_reviews.get_container_client("amazon-reviews").query_items(query=query, enable_cross_partition_query=True))

    word_counts = Counter()
    for item in items:
        reviews = item.get("review", "").split()  # 假设评论数据存储在名为 "review" 的字段中，并使用空格分割单词
        word_counts.update(reviews)

    return word_counts

# @app.route('/query', method=['GET'])
# def show_query():
#     data = query_data(city_name="burton", include_header=True, exact_match=False)
#     return render_template('query.html', data=data)

@app.route('/data', methods=['GET'])
def show_data():
    data = fetch_data(city_name=None, include_header=True, exact_match=False)
    return render_template('data.html', data=data)

# @app.route('/popular_words', methods=['GET'])
# def show_popular_word():
#     data = popular_words()
#     return render_template('popular_words.html', data=data)
# def fetch_data(city_name = None, include_header = False, exact_match = False):
#     with open("us-cities.csv") as csvfile:
#         csvreader = csv.reader(csvfile, delimiter=',', quotechar='|')
#         row_id = -1
#         wanted_data = []
#         for row in csvreader:
#             row_id += 1
#             if row_id == 0 and not include_header:
#                 continue
#             line = []
#             col_id = -1
#             is_wanted_row = False
#             if city_name is None:
#                 is_wanted_row = True
#             for raw_col in row:
#                 col_id += 1
#                 col = raw_col.replace('"', '')
#                 line.append( col )
#                 if col_id == 0 and city_name is not None:
#                     if not exact_match and city_name.lower() in col.lower():
#                         is_wanted_row = True
#                     elif exact_match and city_name.lower() == col.lower():
#                         is_wanted_row = True
#             if is_wanted_row:
#                 if row_id > 0:
#                     line.insert(0, "{}".format(row_id))
#                 else:
#                     line.insert(0, "")
#                 wanted_data.append(line)
#     return wanted_data


# # from flask import request
# @app.route('/data', methods=['GET'])
# def query():
#     city_name = request.args.get('city_name')
#     if city_name is not None:
#         city_name = city_name.replace('"', '')
#     wanted_data = fetch_data(city_name = city_name, include_header = True)
#     table_content = ""
#     for row in wanted_data:
#         line_str = ""
#         for col in row:
#             line_str += "<td>" + col + "</td>"
#         table_content += "<tr>" + line_str + "</tr>"
#     page = "<html><title>Ass2</title><body>"
#     page += "<table>" + table_content + "</table>"
#     page += "</body></html>"
#     return page


# def append_or_update_data(req):
#     city_name = req['city_name']
#     lat = req['lat']
#     lng = req['lng']
#     country = req['country']
#     state = req['state']
#     population = req['population']

#     if city_name is None:
#         return False

#     input_line = '"{}","{}","{}","{}","{}","{}"'.format(
#         city_name, lat, lng, country, state, population,
#     )

#     existing_records = fetch_data(city_name = city_name, exact_match=True)
#     if len(existing_records) == 0:
#         with open('us-cities.csv', 'a') as f:
#             f.write(input_line)
#             f.close()
#     else:
#         all_records = fetch_data(include_header=True)
#         lines = []
#         for row in all_records:
#             line_to_write = ""
#             if row[1].lower() != city_name.lower():
#                 line_to_write = ",".join(['"{}"'.format(col) for col in row[1:]])
#             else:
#                 line_to_write = input_line
#             lines.append(line_to_write + "\n")
#         with open('us-cities.csv', 'w') as f:
#             f.writelines(lines)
#             f.close()
#     return True

# @app.route('/data', methods=['PUT'])
# def append_or_update():
#     req = request.json

#     if append_or_update_data(req):
#         return "done"
#     else:
#         return "invalid input"
    





# from flask import Flask, request, jsonify
# import pandas as pd

# # app = Flask(__name__)

# # Read CSV files and preprocess data
# amazon_reviews = pd.read_csv('static/amazon-reviews.csv')
# us_cities = pd.read_csv('static/us-cities.csv')

# # Function to process popular words
# def get_popular_words(city_name=None, limit=None):
#     if city_name:
#         # Filter reviews based on the given city name
#         city_reviews = amazon_reviews[amazon_reviews['city'] == city_name]
#     else:
#         city_reviews = amazon_reviews  # Use all reviews if city_name is not provided
    
#     # Process reviews to count word occurrences
#     word_count = {}
#     for review in city_reviews['review']:
#         words = review.split()  # Split review into words
#         for word in words:
#             if word in word_count:
#                 word_count[word] += 1
#             else:
#                 word_count[word] = 1
    
#     # Create a list of word popularity as dicts
#     popular_words_list = [{"term": k, "popularity": v} for k, v in word_count.items()]
    
#     # Sort the popular words by popularity in descending order
#     popular_words_list.sort(key=lambda x: x['popularity'], reverse=True)

#     # If limit is provided, slice the list to return only 'limit' number of words
#     if limit is not None and limit < len(popular_words_list):
#         popular_words_list = popular_words_list[:limit]

#     return popular_words_list

# # Route to handle GET requests for popular words
# @app.route('/popular_words', methods=['GET'])
# def popular_words():
#     city_name = request.args.get('city')
#     limit = int(request.args.get('limit')) if 'limit' in request.args else None

#     # Get popular words for the given city and limit
#     popular_words_list = get_popular_words(city_name, limit)

#     return jsonify(popular_words_list)

# if __name__ == '__main__':
#     app.run(debug=True)

# from flask import Flask, request, jsonify
# import pandas as pd


# # Assuming data is loaded into pandas DataFrames
# amazon_reviews = pd.read_csv('static/amazon-reviews.csv')
# us_cities = pd.read_csv('static/us-cities.csv')


# @app.route('/popular_words', methods=['GET'])
# def popular_words():
#     city_name = request.args.get('city')
#     limit = int(request.args.get('limit')) if 'limit' in request.args else None

#     # Filter reviews based on city name
#     if city_name:
#         city_reviews = amazon_reviews[amazon_reviews['city'] == city_name]
#     else:
#         city_reviews = amazon_reviews

#     # Count occurrences of words per city
#     word_count_per_city = {}
#     for index, row in city_reviews.iterrows():
#         city = row['city']
#         words = row['review'].split()
#         unique_cities_for_review = row['unique_cities'].split(',') if 'unique_cities' in row else []  # Assuming 'unique_cities' column exists
#         for word in words:
#             if word in word_count_per_city:
#                 word_count_per_city[word].add(city)
#             else:
#                 word_count_per_city[word] = {city}
            
#             word_count_per_city[word] |= set(unique_cities_for_review)  # Add other cities where the word is mentioned

#     # Calculate the popularity based on city populations
#     word_popularity = {}
#     for word, cities in word_count_per_city.items():
#         word_popularity[word] = sum(us_cities[us_cities['city'].isin(cities)]['population'])  # Assuming 'population' column exists in us_cities

#     # Sort words by their popularity in descending order
#     sorted_words = sorted(word_popularity.items(), key=lambda x: x[1], reverse=True)

#     # Prepare response as a list of dictionaries
#     response = [{"term": word, "popularity": count} for word, count in sorted_words]

#     # Limit the response to 'limit' number of words if limit is provided
#     if limit is not None and limit < len(response):
#         response = response[:limit]

#     return jsonify(response)

# @app.route('/popular_words', methods=['GET'])
# def popular_words():
#     city_name = request.args.get('city')
#     limit = int(request.args.get('limit')) if 'limit' in request.args else None

#     # Filter reviews based on city name
#     if city_name:
#         city_reviews = amazon_reviews[amazon_reviews['city'] == city_name]
#     else:
#         city_reviews = amazon_reviews

#     # Count occurrences of words per city
#     word_count_per_city = {}
#     for index, row in city_reviews.iterrows():
#         city = row['city']
#         words = row['review'].split()
#         for word in words:
#             if word in word_count_per_city:
#                 word_count_per_city[word].add(city)
#             else:
#                 word_count_per_city[word] = {city}

#     # Calculate the popularity based on city populations
#     word_popularity = {}
#     for word, cities in word_count_per_city.items():
#         if len(cities) >= 3:
#             city_populations = us_cities[us_cities['city'].isin(cities)]['population'].tolist()
#             word_popularity[word] = sum(city_populations)

#     # Sort words by their popularity in descending order
#     sorted_words = sorted(word_popularity.items(), key=lambda x: x[1], reverse=True)

#     # Prepare response as a list of dictionaries
#     response = [{"term": word, "popularity": count} for word, count in sorted_words]

#     # Limit the response to 'limit' number of words if limit is provided
#     if limit is not None and limit < len(response):
#         response = response[:limit]

#     return jsonify(response)

# @app.route('/substitute_words', methods=['POST'])
# def substitute_words():
#     request_data = request.get_json()

#     if 'word' not in request_data or 'substitute' not in request_data:
#         return jsonify({"error": "Invalid request format"}), 400

#     word_to_replace = request_data['word']
#     substitute_word = request_data['substitute']

#     affected_reviews = perform_word_substitution(word_to_replace, substitute_word)

#     response = {"affected_reviews": affected_reviews}
#     return jsonify(response)

# def perform_word_substitution(word_to_replace, substitute_word):
#     affected_reviews_count = 0

#     global reviews  # Assume this variable holds the reviews data

#     for i, review in enumerate(reviews):
#         if word_to_replace in review:
#             reviews[i] = review.replace(word_to_replace, substitute_word)
#             affected_reviews_count += 1

#     return affected_reviews_count
# Endpoint to get popular words
# @app.route('/popular_words', methods=['GET'])
# def get_popular_words():
#     city_name = request.args.get('city')
#     limit = int(request.args.get('limit')) if 'limit' in request.args else None

#     # Filter reviews based on the city
#     if city_name:
#         city_reviews = amazon_reviews[amazon_reviews['city'] == city_name]
#     else:
#         city_reviews = amazon_reviews

#     # Count occurrences of words
#     word_count = {}
#     for review in city_reviews['review']:
#         words = review.split()
#         for word in words:
#             if word in word_count:
#                 word_count[word] += 1
#             else:
#                 word_count[word] = 1

#     # Sort words by their counts in descending order
#     sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)

#     # Prepare the response in the specified format
#     response = [{"term": word, "popularity": count} for word, count in sorted_words]

#     # Limit the response to 'limit' number of words if limit is provided
#     if limit is not None and limit < len(response):
#         response = response[:limit]

#     return jsonify(response)






# @app.route('/popular_words', methods=['GET'])
# def popular_words():
#     city_name = request.args.get('city')
#     limit = int(request.args.get('limit')) if 'limit' in request.args else None

#     # Filter reviews based on city name
#     if city_name:
#         city_reviews = amazon_reviews[amazon_reviews['city'] == city_name]
#     else:
#         city_reviews = amazon_reviews

#     # Count occurrences of words
#     word_count = {}
#     for review in city_reviews['review']:
#         words = review.split()
#         for word in words:
#             if word in word_count:
#                 word_count[word] += 1
#             else:
#                 word_count[word] = 1

#     # Sort words by their counts in descending order
#     sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)

#     # Prepare response as a list of dictionaries
#     response = [{"term": word, "popularity": count} for word, count in sorted_words]

#     # Limit the response to 'limit' number of words if limit is provided
#     if limit is not None and limit < len(response):
#         response = response[:limit]

#     return jsonify(response)

# if __name__ == '__main__':
#     app.run(debug=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8084, debug=True)