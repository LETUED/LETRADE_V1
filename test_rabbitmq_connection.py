#!/usr/bin/env python3
"""
RabbitMQ 연결 테스트 스크립트
"""

import asyncio
import os
import sys
from src.common.message_bus import MessageBus


async def test_rabbitmq_connection():
    """RabbitMQ 연결 및 기본 기능 테스트"""
    
    # 기존 컨테이너 설정 사용
    config = {
        "host": "localhost",
        "port": 5672,
        "username": "letrade_user",
        "password": "letrade_password",  # 실제 값
        "virtual_host": "/"
    }
    
    print("🐰 RabbitMQ 연결 테스트 시작...")
    print(f"연결 정보: {config['username']}@{config['host']}:{config['port']}")
    
    bus = MessageBus(config)
    
    try:
        # 연결 시도
        print("\n1. 연결 시도...")
        success = await bus.connect()
        
        if not success:
            print("❌ RabbitMQ 연결 실패")
            return False
        
        print("✅ RabbitMQ 연결 성공!")
        
        # 헬스체크
        print("\n2. 헬스체크...")
        health = await bus.health_check()
        print(f"헬스체크 결과: {health}")
        
        # 간단한 메시지 발행/구독 테스트
        print("\n3. 메시지 발행 테스트...")
        
        test_message = {
            "test": True,
            "message": "Hello RabbitMQ!",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        # 메시지 발행
        publish_success = await bus.publish(
            exchange_name="letrade.events",
            routing_key="events.test.message",
            message=test_message
        )
        
        if publish_success:
            print("✅ 메시지 발행 성공!")
        else:
            print("❌ 메시지 발행 실패")
        
        # 연결 해제
        print("\n4. 연결 해제...")
        await bus.disconnect()
        print("✅ 연결 해제 완료")
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        if bus.is_connected:
            await bus.disconnect()
        return False


async def test_different_credentials():
    """다른 인증 정보로 시도"""
    
    credentials_to_try = [
        ("letrade_user", "letrade_password"),
        ("guest", "guest"),
        ("admin", "admin"),
        ("letrade_user", "letrade_pass"),
        ("letrade_user", "letrade123")
    ]
    
    for username, password in credentials_to_try:
        config = {
            "host": "localhost",
            "port": 5672,
            "username": username,
            "password": password,
            "virtual_host": "/"
        }
        
        print(f"\n🔐 시도 중: {username}/{password}")
        
        bus = MessageBus(config)
        
        try:
            success = await bus.connect()
            if success:
                print(f"✅ 성공! 사용자: {username}, 비밀번호: {password}")
                await bus.disconnect()
                return config
            else:
                print(f"❌ 실패: {username}/{password}")
        except Exception as e:
            print(f"❌ 오류: {username}/{password} - {e}")
        
        if bus.is_connected:
            await bus.disconnect()
    
    return None


async def main():
    """메인 테스트 함수"""
    
    print("="*60)
    print("🚀 Letrade RabbitMQ 연결 테스트")
    print("="*60)
    
    # 먼저 기본 설정으로 시도
    success = await test_rabbitmq_connection()
    
    if not success:
        print("\n기본 설정 실패, 다른 인증 정보 시도...")
        working_config = await test_different_credentials()
        
        if working_config:
            print(f"\n✅ 작동하는 설정 발견:")
            print(f"   사용자명: {working_config['username']}")
            print(f"   비밀번호: {working_config['password']}")
            
            # 환경변수 설정 제안
            print(f"\n📝 환경변수 설정 제안:")
            print(f"export RABBITMQ_HOST=localhost")
            print(f"export RABBITMQ_PORT=5672")
            print(f"export RABBITMQ_USERNAME={working_config['username']}")
            print(f"export RABBITMQ_PASSWORD={working_config['password']}")
            print(f"export RABBITMQ_VHOST=/")
        else:
            print("\n❌ 모든 인증 시도 실패")
            print("RabbitMQ 컨테이너를 새로 설정해야 할 수 있습니다.")
    
    print("\n" + "="*60)
    print("🏁 테스트 완료")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())