# 使用 locust 的官方映像作為基礎
FROM locustio/locust

# 安裝 python-socketio
RUN pip install python-socketio asyncio 
