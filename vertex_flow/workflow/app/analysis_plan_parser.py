#!/usr/bin/env python3
"""
分析计划解析器

用于解析JSON格式的分析计划，提取分析步骤信息
"""

import json
import logging
from typing import Any, Dict, List

from vertex_flow.utils.logger import LoggerUtil

logger = LoggerUtil.get_logger()


def parse_analysis_plan(plan_input: str) -> List[Dict[str, Any]]:
    """
    解析分析计划，支持JSON格式或普通文本

    Args:
        plan_input: 分析计划输入（JSON字符串或普通文本）

    Returns:
        List[Dict]: 解析后的步骤列表

    Raises:
        ValueError: 当输入格式完全无法解析时
    """
    if not plan_input or not isinstance(plan_input, str):
        logger.warning("分析计划输入为空或非字符串类型")
        raise ValueError("分析计划输入无效")

    plan_input = plan_input.strip()
    logger.info(f"开始解析分析计划，输入长度: {len(plan_input)}")

    try:
        # 首先尝试解析为JSON
        plan_data = json.loads(plan_input)
        logger.info(f"成功解析分析计划JSON")

        # 提取步骤列表
        if "steps" not in plan_data:
            logger.warning("分析计划JSON中缺少'steps'字段，尝试其他解析方式")
            raise ValueError("分析计划JSON中缺少'steps'字段")

        steps = plan_data["steps"]
        if not isinstance(steps, list):
            logger.warning("'steps'字段不是列表类型，尝试其他解析方式")
            raise ValueError("'steps'字段必须是列表类型")

        # 验证和标准化步骤数据
        validated_steps = []
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                logger.warning(f"步骤 {i+1} 不是字典类型，跳过")
                continue

            # 标准化步骤数据
            validated_step = {
                "step_id": step.get("step_id", f"step_{i+1}"),
                "step_name": step.get("step_name", f"步骤{i+1}"),
                "description": step.get("description", "无描述"),
                "method": step.get("method", "通用分析"),
                "dependencies": step.get("dependencies", []),
            }

            validated_steps.append(validated_step)
            logger.debug(f"验证步骤: {validated_step['step_id']} - {validated_step['step_name']}")

        if validated_steps:
            logger.info(f"成功解析 {len(validated_steps)} 个分析步骤")
            return validated_steps
        else:
            logger.warning("JSON中没有有效的步骤数据，尝试文本解析")
            raise ValueError("JSON中没有有效的步骤数据")

    except (json.JSONDecodeError, ValueError) as e:
        logger.info(f"JSON解析失败 ({str(e)})，尝试从文本中提取JSON")

        # 尝试从文本中提取JSON部分
        try:
            json_steps = _extract_json_from_text(plan_input)
            if json_steps:
                logger.info(f"从文本中成功提取JSON，解析到 {len(json_steps)} 个分析步骤")
                return json_steps
        except Exception as json_e:
            logger.warning(f"JSON提取失败: {json_e}")

        # 尝试从文本中提取步骤信息
        try:
            text_steps = _parse_text_plan(plan_input)
            if text_steps:
                logger.info(f"从文本中成功提取 {len(text_steps)} 个分析步骤")
                return text_steps
        except Exception as text_e:
            logger.warning(f"文本解析也失败: {text_e}")

        # 如果所有解析方式都失败，抛出异常
        error_msg = f"分析计划解析失败，既不是有效JSON也无法从文本中提取步骤信息: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)


def _extract_json_from_text(text: str) -> List[Dict[str, Any]]:
    """
    从文本中提取JSON部分并解析

    Args:
        text: 包含JSON的文本

    Returns:
        List[Dict]: 解析后的步骤列表
    """
    import re

    # 尝试匹配JSON对象
    json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    json_matches = re.findall(json_pattern, text, re.DOTALL)

    for json_str in json_matches:
        try:
            # 尝试解析JSON
            data = json.loads(json_str)
            if "steps" in data and isinstance(data["steps"], list):
                steps = data["steps"]
                validated_steps = []

                for i, step in enumerate(steps):
                    if isinstance(step, dict):
                        validated_step = {
                            "step_id": step.get("step_id", f"step_{i+1}"),
                            "step_name": step.get("step_name", f"步骤{i+1}"),
                            "description": step.get("description", "无描述"),
                            "method": step.get("method", "通用分析"),
                            "dependencies": step.get("dependencies", []),
                        }
                        validated_steps.append(validated_step)

                if validated_steps:
                    logger.info(f"成功从文本中提取JSON并解析 {len(validated_steps)} 个步骤")
                    return validated_steps
        except json.JSONDecodeError:
            continue

    # 如果没有找到有效的JSON，返回空列表
    return []


def _parse_text_plan(text: str) -> List[Dict[str, Any]]:
    """
    从普通文本中解析分析步骤

    Args:
        text: 包含分析步骤的文本

    Returns:
        List[Dict]: 解析后的步骤列表
    """
    steps = []
    lines = text.split("\n")
    current_step = None
    step_counter = 1

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 检测步骤标题（数字开头或包含"步骤"关键词）
        if (
            line.startswith(("1.", "2.", "3.", "4.", "5."))
            or "步骤" in line
            or line.startswith(("第一", "第二", "第三", "第四", "第五"))
            or line.startswith(("一、", "二、", "三、", "四、", "五、"))
        ):

            # 保存前一个步骤
            if current_step:
                steps.append(current_step)

            # 开始新步骤
            current_step = {
                "step_id": f"step_{step_counter}",
                "step_name": line,
                "description": "",
                "method": "通用分析",
                "dependencies": [],
            }
            step_counter += 1

        elif current_step and line:
            # 添加到当前步骤的描述中
            if current_step["description"]:
                current_step["description"] += " " + line
            else:
                current_step["description"] = line

    # 添加最后一个步骤
    if current_step:
        steps.append(current_step)

    # 如果没有找到明确的步骤，将整个文本作为一个步骤
    if not steps and text:
        steps.append(
            {
                "step_id": "step_1",
                "step_name": "分析步骤",
                "description": text[:200] + "..." if len(text) > 200 else text,
                "method": "通用分析",
                "dependencies": [],
            }
        )

    return steps


def create_default_analysis_plan(research_topic: str) -> List[Dict[str, Any]]:
    """
    为研究主题创建默认的分析计划

    Args:
        research_topic: 研究主题

    Returns:
        List[Dict]: 默认分析步骤列表
    """
    default_steps = [
        {
            "step_id": "current_status_analysis",
            "step_name": "现状分析",
            "description": f"分析'{research_topic}'的当前发展状况、主要特点和关键参与者",
            "method": "现状调研分析",
            "dependencies": [],
        },
        {
            "step_id": "trend_analysis",
            "step_name": "趋势分析",
            "description": f"识别'{research_topic}'的发展趋势、变化模式和未来方向",
            "method": "趋势分析法",
            "dependencies": ["current_status_analysis"],
        },
        {
            "step_id": "impact_assessment",
            "step_name": "影响评估",
            "description": f"评估'{research_topic}'对相关领域和社会的影响",
            "method": "影响评估分析",
            "dependencies": ["trend_analysis"],
        },
        {
            "step_id": "solution_analysis",
            "step_name": "解决方案分析",
            "description": f"分析'{research_topic}'相关的解决方案、最佳实践和创新方法",
            "method": "方案分析法",
            "dependencies": ["impact_assessment"],
        },
    ]

    logger.info(f"为研究主题'{research_topic}'创建了 {len(default_steps)} 个默认分析步骤")
    return default_steps


def validate_step_dependencies(steps: List[Dict[str, Any]]) -> bool:
    """
    验证步骤依赖关系的有效性

    Args:
        steps: 步骤列表

    Returns:
        bool: 依赖关系是否有效
    """
    step_ids = {step["step_id"] for step in steps}

    for step in steps:
        dependencies = step.get("dependencies", [])
        for dep in dependencies:
            if dep not in step_ids:
                logger.error(f"步骤 {step['step_id']} 的依赖 {dep} 不存在")
                return False

    logger.info("步骤依赖关系验证通过")
    return True


def sort_steps_by_dependencies(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    根据依赖关系对步骤进行拓扑排序

    Args:
        steps: 步骤列表

    Returns:
        List[Dict]: 排序后的步骤列表
    """
    if not validate_step_dependencies(steps):
        logger.warning("依赖关系验证失败，返回原始顺序")
        return steps

    # 简单的拓扑排序实现
    sorted_steps = []
    remaining_steps = steps.copy()
    processed_ids = set()

    while remaining_steps:
        # 找到没有未处理依赖的步骤
        ready_steps = []
        for step in remaining_steps:
            dependencies = step.get("dependencies", [])
            if all(dep in processed_ids for dep in dependencies):
                ready_steps.append(step)

        if not ready_steps:
            logger.warning("检测到循环依赖，使用原始顺序")
            return steps

        # 添加准备好的步骤
        for step in ready_steps:
            sorted_steps.append(step)
            processed_ids.add(step["step_id"])
            remaining_steps.remove(step)

    logger.info(f"成功对 {len(sorted_steps)} 个步骤进行依赖排序")
    return sorted_steps
