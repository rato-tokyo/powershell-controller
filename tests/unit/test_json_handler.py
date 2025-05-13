"""
JsonHandlerのテスト

JsonHandlerクラスの機能テスト
"""

import pytest

from py_pshell.json_handler import JsonHandler


class TestJsonHandler:
    """JsonHandlerクラスのテスト"""

    def test_get_json_valid_json(self):
        """有効なJSONのパースをテスト"""
        # テスト用のJSONデータ
        json_data = '{"name": "test", "value": 123, "items": [1, 2, 3]}'
        command = "Get-Something | ConvertTo-Json"

        result = JsonHandler.get_json(command, json_data)

        # 正しくパースされたか
        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["value"] == 123
        assert result["items"] == [1, 2, 3]

    def test_get_json_invalid_json(self):
        """無効なJSONのパースをテスト（例外発生）"""
        # 無効なJSONデータ
        invalid_json = '{"name": "test", "value": 123, "items": [1, 2, 3'  # 閉じカッコがない
        command = "Get-Something | ConvertTo-Json"

        with pytest.raises(ValueError) as exc_info:
            JsonHandler.get_json(command, invalid_json)

        # エラーメッセージに元のデータが含まれているか
        assert "JSONの解析に失敗しました" in str(exc_info.value)
        assert invalid_json in str(exc_info.value)

    def test_ensure_json_command_without_json(self):
        """ConvertTo-Jsonが含まれていないコマンドのテスト"""
        command = "Get-Process"
        expected = "Get-Process | ConvertTo-Json -Depth 10"

        result = JsonHandler.ensure_json_command(command)

        # ConvertTo-Jsonが追加されたか
        assert result == expected

    def test_ensure_json_command_with_json(self):
        """既にConvertTo-Jsonが含まれているコマンドのテスト"""
        command = "Get-Process | ConvertTo-Json -Depth 5"

        result = JsonHandler.ensure_json_command(command)

        # コマンドが変更されていないか
        assert result == command

    def test_parse_json_valid_dict(self):
        """有効な辞書JSONのパースをテスト"""
        json_data = '{"name": "test", "value": 123}'
        command = "Get-Something | ConvertTo-Json"

        result = JsonHandler.parse_json(command, json_data)

        # 正しくパースされたか
        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["value"] == 123

    def test_parse_json_not_dict(self):
        """辞書でないJSONのパースをテスト（例外発生）"""
        json_data = "[1, 2, 3]"  # 配列（辞書ではない）
        command = "Get-Something | ConvertTo-Json"

        with pytest.raises(ValueError) as exc_info:
            JsonHandler.parse_json(command, json_data)

        # エラーメッセージに適切な内容が含まれているか
        assert "JSONの解析結果が辞書ではありません" in str(exc_info.value)

    def test_parse_json_invalid_json(self):
        """無効なJSONのパースをテスト（例外発生）"""
        invalid_json = '{name: "test"}'  # 無効なJSON（キーが引用符で囲まれていない）
        command = "Get-Something | ConvertTo-Json"

        with pytest.raises(ValueError) as exc_info:
            JsonHandler.parse_json(command, invalid_json)

        # エラーメッセージに元のデータが含まれているか
        assert "JSONの解析に失敗しました" in str(exc_info.value)
        assert invalid_json in str(exc_info.value)
