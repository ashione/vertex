.PHONY: version-show version-patch version-minor version-major publish publish-test help

# 显示当前版本
version-show:
	@python scripts/version_bump.py show

# 递增补丁版本 (0.1.0 -> 0.1.1)
version-patch:
	@python scripts/version_bump.py patch

# 递增次版本 (0.1.0 -> 0.2.0)
version-minor:
	@python scripts/version_bump.py minor

# 递增主版本 (0.1.0 -> 1.0.0)
version-major:
	@python scripts/version_bump.py major

# 预览版本变更
version-preview-patch:
	@python scripts/version_bump.py patch --dry-run

version-preview-minor:
	@python scripts/version_bump.py minor --dry-run

version-preview-major:
	@python scripts/version_bump.py major --dry-run

# 发布到PyPI (自动递增patch版本)
publish:
	@python scripts/publish.py

# 发布到PyPI (指定版本递增类型)
publish-patch:
	@python scripts/publish.py --bump patch

publish-minor:
	@python scripts/publish.py --bump minor

publish-major:
	@python scripts/publish.py --bump major

# 发布到PyPI (不递增版本)
publish-no-bump:
	@python scripts/publish.py --no-bump

# 发布到TestPyPI
publish-test:
	@python scripts/publish.py --test

# 显示帮助信息
help:
	@echo "版本管理命令:"
	@echo "  version-show          显示当前版本"
	@echo "  version-patch         递增补丁版本 (0.1.0 -> 0.1.1)"
	@echo "  version-minor         递增次版本 (0.1.0 -> 0.2.0)"
	@echo "  version-major         递增主版本 (0.1.0 -> 1.0.0)"
	@echo "  version-preview-*     预览版本变更"
	@echo ""
	@echo "发布命令:"
	@echo "  publish               发布到PyPI (自动递增patch版本)"
	@echo "  publish-patch         发布到PyPI (递增patch版本)"
	@echo "  publish-minor         发布到PyPI (递增minor版本)"
	@echo "  publish-major         发布到PyPI (递增major版本)"
	@echo "  publish-no-bump       发布到PyPI (不递增版本)"
	@echo "  publish-test          发布到TestPyPI"
	@echo ""
	@echo "示例:"
	@echo "  make version-show     # 查看当前版本"
	@echo "  make version-patch    # 递增补丁版本"
	@echo "  make publish-minor    # 递增次版本并发布"