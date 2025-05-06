"""
各種インポートが適切に動作するかのテスト
"""
import warnings
import pytest

def test_simple_import_works():
    """simple.pyからのインポートが正常に動作するかをテスト"""
    # simple.pyからインポート
    from powershell_controller.simple import SimplePowerShellController
    
    # インポートしたクラスが使用可能であることを確認
    controller = SimplePowerShellController()
    assert controller is not None
    
    # CommandResultもインポートできることを確認
    from powershell_controller.simple import CommandResult
    
    # 基本的な機能が動作することを確認
    result = CommandResult(output="テスト", success=True)
    assert result.output == "テスト"
    assert result.success is True

def test_init_import_works():
    """__init__.pyからのインポートが正常に動作するかをテスト"""
    # __init__.pyからインポート
    from powershell_controller import SimplePowerShellController
    
    # インポートしたクラスが使用可能であることを確認
    controller = SimplePowerShellController()
    assert controller is not None
    
    # CommandResultもインポートできることを確認
    from powershell_controller import CommandResult
    
    # 基本的な機能が動作することを確認
    result = CommandResult(output="テスト", success=True)
    assert result.output == "テスト"
    assert result.success is True

def test_import_fails_for_nonexistent_controller():
    """削除されたcontroller.pyからのインポートが失敗することを確認するテスト"""
    with pytest.raises(ImportError):
        # このインポートは失敗するはず
        from powershell_controller.controller import SimplePowerShellController 