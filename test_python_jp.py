#!/usr/bin/env python
# -*- coding: utf-8 -*-

def main():
    text = "Pythonでの日本語テスト"
    print(f"日本語テキスト: {text}")
    print(f"文字数: {len(text)}")
    
    # エンコード/デコードのテスト
    encoded = text.encode('utf-8')
    decoded = encoded.decode('utf-8')
    print(f"エンコード: {encoded}")
    print(f"デコード: {decoded}")
    
    return 0

if __name__ == "__main__":
    main() 