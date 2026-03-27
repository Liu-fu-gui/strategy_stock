c[root@docker ~/stock]$ cat docker-compose.yaml 
version: "3.8"

services:
  postgres:
    image: swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/postgres:18.3
    container_name: pg_stock
    restart: unless-stopped
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: stock
      POSTGRES_PASSWORD: stock123456
    ports:
      - "5432:5432"
    volumes:
      - ./postgres:/var/lib/postgresql

  redis:
    image: swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/redis:6.2.20-alpine
    container_name: redis_stock
    restart: unless-stopped
    command:
      - redis-server
      - --appendonly
      - "yes"
      - --requirepass
      - redis123456
    ports:
      - "6380:6379"
    volumes:
      - ./redis:/data
这个是redis 和pg存储

http://xtick.top/
token是0d8aa771dd0a0e33624e1546d13c3eb6


这个是竞价筛选策略
低吸：近5日有涨停，近3日回调超过5%，今日9.25分前竞价抢筹且竞价金额大于1000万，流通市值大于50亿小于300亿非科创，非创业，非北交所，非st的股票