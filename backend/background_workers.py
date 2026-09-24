# -*- coding: utf-8 -*-
"""
Background Workers cho hệ thống Smart Shopping Assistant.
Chạy các tác vụ nền: phân tích bình luận, cập nhật PQS/RQS, đồng bộ dữ liệu.
"""
import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient

import comment_analyzer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


class CommentAnalysisWorker:
    """Worker phân tích bình luận offline và lưu kết quả vào MongoDB."""
    
    def __init__(self, mongo_uri: str, db_name: str = "price_tracker", load_phobert: bool = True):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.client = None
        self.db = None
        self.tokenizer = None
        self.model_sent = None
        self.model_aspect = None
        if load_phobert:
            comment_analyzer.load_label_maps()
            tok, ms, ma = comment_analyzer.load_models()
            self.tokenizer, self.model_sent, self.model_aspect = tok, ms, ma
            logger.info("✅ Nạp PhoBERT sentiment/aspect models cho Worker thành công")
    
    async def connect(self):
        """Kết nối MongoDB."""
        self.client = AsyncIOMotorClient(self.mongo_uri)
        self.db = self.client[self.db_name]
        logger.info("✅ Kết nối MongoDB thành công")
    
    async def disconnect(self):
        """Đóng kết nối."""
        if self.client:
            self.client.close()
            logger.info("🔌 Đã đóng kết nối MongoDB")
    
    async def analyze_product_comments(self, product_id: str, platform: str) -> Dict[str, Any]:
        """Phân tích tất cả bình luận của một sản phẩm và tính RQS/PQS tổng hợp.
        
        Args:
            product_id: ID sản phẩm trong MongoDB
            platform: Tên sàn thương mại
        
        Returns:
            Dict chứa kết quả phân tích
        """
        # Lấy sản phẩm và bình luận
        col_name = self._get_collection_name(platform)
        col = self.db[col_name]
        
        product = await col.find_one({"_id": product_id})
        if not product:
            return {"error": "Product not found"}
        
        comments = product.get('comments', [])
        if not comments:
            return {"error": "No comments"}
        
        # Phân tích từng bình luận
        sentiment_data = self._analyze_comments_batch(comments)
        
        # Tính RQS trung bình
        rqs_list = [c.get('rqs', 0) for c in sentiment_data.get('list', [])]
        avg_rqs = sum(rqs_list) / len(rqs_list) if rqs_list else 0
        
        # Cập nhật vào MongoDB
        await col.update_one(
            {"_id": product_id},
            {
                "$set": {
                    "sentiment_analysis": sentiment_data,
                    "avg_rqs": avg_rqs,
                    "comment_count": len(comments),
                    "analyzed_at": datetime.now(timezone.utc)
                }
            }
        )
        
        return {
            "product_id": str(product_id),
            "platform": platform,
            "comment_count": len(comments),
            "avg_rqs": avg_rqs,
            "sentiment_distribution": sentiment_data.get('distribution', {})
        }
    
    async def batch_analyze_platform(self, platform: str, batch_size: int = 50) -> Dict[str, int]:
        """Phân tích hàng loạt sản phẩm của một sàn.
        
        Args:
            platform: Tên sàn thương mại
            batch_size: Số sản phẩm xử lý mỗi batch
        
        Returns:
            Thống kê kết quả
        """
        col_name = self._get_collection_name(platform)
        col = self.db[col_name]
        
        # Lấy sản phẩm có bình luận nhưng chưa phân tích
        cursor = col.find({
            "comments": {"$exists": True, "$ne": []},
            "sentiment_analysis": {"$exists": False}
        }).limit(batch_size)
        
        products = await cursor.to_list(length=batch_size)
        logger.info(f"📊 [{platform}] Tìm thấy {len(products)} sản phẩm cần phân tích")
        
        stats = {"total": len(products), "success": 0, "failed": 0}
        
        for product in products:
            try:
                result = await self.analyze_product_comments(product['_id'], platform)
                if 'error' not in result:
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
            except Exception as e:
                logger.error(f"❌ Lỗi phân tích {product.get('name', '')}: {e}")
                stats['failed'] += 1
        
        logger.info(f"✅ [{platform}] Hoàn thành: {stats['success']} thành công, {stats['failed']} thất bại")
        return stats
    
    async def analyze_all_platforms(self, platforms: List[str], batch_size: int = 50) -> Dict[str, Dict]:
        """Phân tích tất cả sàn.
        
        Args:
            platforms: Danh sách tên sàn
            batch_size: Số sản phẩm mỗi batch
        
        Returns:
            Thống kê theo từng sàn
        """
        results = {}
        for platform in platforms:
            stats = await self.batch_analyze_platform(platform, batch_size)
            results[platform] = stats
        return results
    
    def _get_collection_name(self, platform: str) -> str:
        """Map tên sàn sang tên collection."""
        mapping = {
            "FPT Shop": "fpt",
            "Thế Giới Di Động": "tgdd",
            "CellphoneS": "cellphones",
            "Hoàng Hà Mobile": "hoangha",
            "Di Động Việt": "didongviet",
            "Viettel Store": "viettelstore",
            "Clickbuy": "clickbuy",
            "MobileCity": "mobilecity",
        }
        return mapping.get(platform, platform.lower().replace(' ', '_'))
    
    def _analyze_comments_batch(self, comments: List[Dict]) -> Dict[str, Any]:
        """Phân tích batch bình luận dùng PhoBERT + rule-based hybrid engine (đồng bộ với API)."""
        return comment_analyzer.analyze_comments(
            comments,
            tokenizer=self.tokenizer,
            model_sent=self.model_sent,
            model_aspect=self.model_aspect
        )


async def main():
    """Main entry point cho worker."""
    import argparse
    parser = argparse.ArgumentParser(description="Background Worker cho phân tích bình luận")
    parser.add_argument("--platform", type=str, help="Tên sàn cụ thể")
    parser.add_argument("--all", action="store_true", help="Chạy tất cả sàn")
    parser.add_argument("--batch-size", type=int, default=50, help="Số sản phẩm mỗi batch")
    args = parser.parse_args()
    
    MONGO_URI = os.environ.get(
        "MONGO_URI",
        "mongodb+srv://22050040_db_user:Accnam55@giasanpham.uqyaw1p.mongodb.net/?appName=GiaSanPham"
    )
    
    worker = CommentAnalysisWorker(MONGO_URI)
    await worker.connect()
    
    try:
        if args.all:
            platforms = [
                "FPT Shop", "Thế Giới Di Động", "CellphoneS", "Hoàng Hà Mobile",
                "Di Động Việt", "Viettel Store", "Clickbuy", "MobileCity"
            ]
            results = await worker.analyze_all_platforms(platforms, args.batch_size)
            print("\n" + "="*80)
            print("TỔNG KẾT PHÂN TÍCH BÌNH LUẬN")
            print("="*80)
            for platform, stats in results.items():
                print(f"  {platform}: {stats['success']} thành công, {stats['failed']} thất bại")
        elif args.platform:
            stats = await worker.batch_analyze_platform(args.platform, args.batch_size)
            print(f"\n✅ {args.platform}: {stats['success']} thành công, {stats['failed']} thất bại")
        else:
            parser.print_help()
    finally:
        await worker.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
