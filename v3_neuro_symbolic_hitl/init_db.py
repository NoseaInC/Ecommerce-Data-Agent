# init_db.py
import os
import sqlite3
import random
from datetime import datetime, timedelta
from core.config import DB_PATH

def initialize_database():
    print(f"📦 正在初始化 [多表关联] 测试数仓: {DB_PATH}")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # ==========================================
    # 建表：标准的星型模型 (1个事实表 + 1个明细表 + 2个维度表)
    # ==========================================
    # 1. 用户维度表 (users)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            register_date TEXT,
            city_tier TEXT,
            is_vip INTEGER,
            gender TEXT
        )
    ''')
    
    # 2. 商品维度表 (products)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            category TEXT,
            brand TEXT,
            base_price REAL
        )
    ''')
    
    # 3. 订单事实表 (orders)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id TEXT,
            order_time TEXT,
            total_amount REAL,
            actual_pay REAL,
            order_status TEXT
        )
    ''')
    
    # 4. 订单明细表 (order_items)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            item_id TEXT PRIMARY KEY,
            order_id TEXT,
            product_id TEXT,
            quantity INTEGER,
            is_refunded INTEGER
        )
    ''')
    
    # 清空旧数据
    for table in ['users', 'products', 'orders', 'order_items']:
        cursor.execute(f"DELETE FROM {table}")
        
    print("   => 正在生成维度数据 (Users, Products)...")
    
    # 生成 User 数据 (3000个用户)
    users_data = []
    city_tiers = ['一线', '二线', '三线', '四线', '五线']
    for i in range(1, 3001):
        uid = f"U{i:05d}"
        reg_date = (datetime(2022, 1, 1) + timedelta(days=random.randint(0, 600))).strftime("%Y-%m-%d")
        city = random.choices(city_tiers, weights=[0.3, 0.3, 0.2, 0.15, 0.05])[0]
        is_vip = random.choices([1, 0], weights=[0.2, 0.8])[0]
        gender = random.choice(['M', 'F'])
        users_data.append((uid, reg_date, city, is_vip, gender))
    cursor.executemany("INSERT INTO users VALUES (?,?,?,?,?)", users_data)
    
    # 生成 Product 数据 (500个商品)
    products_data = []
    categories = ['3C数码', '美妆个护', '服饰内衣', '家居日用', '食品生鲜']
    for i in range(1, 501):
        pid = f"P{i:04d}"
        cat = random.choice(categories)
        base_price = {'3C数码': 2500, '美妆个护': 400, '服饰内衣': 200, '家居日用': 80, '食品生鲜': 50}[cat] * random.uniform(0.5, 2.0)
        brand = f"Brand_{random.randint(1, 50)}"
        products_data.append((pid, cat, brand, round(base_price, 2)))
    cursor.executemany("INSERT INTO products VALUES (?,?,?,?)", products_data)
    
    print("   => 正在生成事实数据 (Orders, OrderItems)...")
    
    # 生成 Order 和 OrderItem 数据 (10000个主订单，可能裂变为万级明细)
    orders_data = []
    order_items_data = []
    
    start_time = datetime(2023, 10, 31, 20, 0, 0)
    item_counter = 1
    
    for i in range(1, 10001):
        order_id = f"ORD{i:06d}"
        user = random.choice(users_data)
        user_id = user[0]
        
        # 模拟双十一时间分布：带精确到秒的时间戳！
        if random.random() < 0.4:
            otime = datetime(2023, 11, 11, random.randint(0, 23), random.randint(0, 59), random.randint(0, 59))
        else:
            otime = start_time + timedelta(days=random.randint(0, 10), hours=random.randint(0, 23), minutes=random.randint(0, 59))
            
        order_time_str = otime.strftime("%Y-%m-%d %H:%M:%S")
        
        # 订单明细 (1到3个商品)
        num_items = random.randint(1, 3)
        total_amount = 0
        for _ in range(num_items):
            prod = random.choice(products_data)
            prod_id = prod[0]
            cat = prod[1]
            price = prod[3]
            qty = random.randint(1, 2)
            
            # 业务逻辑：服饰退款率高，VIP退款率略低
            refund_prob = 0.15 if cat == '服饰内衣' else 0.05
            if user[3] == 1: refund_prob -= 0.02 
            is_ref = 1 if random.random() < max(0, refund_prob) else 0
            
            order_items_data.append((f"ITM{item_counter:07d}", order_id, prod_id, qty, is_ref))
            item_counter += 1
            total_amount += price * qty
            
        # 优惠逻辑 (VIP 8折，非VIP 9折)
        discount = 0.8 if user[3] == 1 else 0.9
        actual_pay = total_amount * discount
        
        orders_data.append((order_id, user_id, order_time_str, round(total_amount, 2), round(actual_pay, 2), 'COMPLETED'))
        
    cursor.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?)", orders_data)
    cursor.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)", order_items_data)
    
    conn.commit()
    conn.close()
    print(f"✅ 模拟数据插入成功！")
    print(f"   - users 表: {len(users_data)} 行")
    print(f"   - products 表: {len(products_data)} 行")
    print(f"   - orders 表: {len(orders_data)} 行")
    print(f"   - order_items 表: {len(order_items_data)} 行")

if __name__ == "__main__":
    initialize_database()