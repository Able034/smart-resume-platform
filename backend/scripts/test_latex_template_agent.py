import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
DEFAULT_TEMPLATE = PROJECT_ROOT / "templates" / "resume" / "tech.tex"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "generated" / "latex"

sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.latex_template_agent import LatexTemplateAgent  # noqa: E402
from app.schemas.resume import AwardDTO, EducationDTO, ProjectDTO, ResumeDetail  # noqa: E402


def build_sample_resume() -> ResumeDetail:
    return ResumeDetail(
        resume_id=0,
        user_id=0,
        title="Java 后端开发简历",
        name="肖勇友",
        age=None,
        email="23yyxiao@stu.edu.cn",
        phone="13025286381",
        expected_position="Java 后端开发实习",
        expected_salary=None,
        skill_name="Java；Spring Boot；MySQL；Redis；RabbitMQ；Neo4j；LangChain",
        personal_context="熟悉 Java 后端开发和 AI 应用开发，具备项目落地经验。",
        status="DRAFT",
        educations=[
            EducationDTO(
                education_info_id=1,
                university="汕头大学",
                major="计算机科学与技术",
                degree="本科",
                start_time="2023-09-01",
                end_time="2027-06-01",
            )
        ],
        projects=[
            ProjectDTO(
                project_info_id=1,
                project_name="TCMSeek 中医药知识图谱与 AI 问答平台",
                role="核心开发",
                introduction="面向中医药研究场景的知识图谱与 AI 问答平台。",
                content=(
                    "负责 Neo4j 图谱查询接口、EasyExcel 导入组件和 AI 服务拆分；"
                    "基于 RabbitMQ + Redis 改造耗时任务；"
                    "通过 Tool Calling 封装受控图谱工具。"
                ),
                start_time=None,
                end_time=None,
            )
        ],
        interns=[],
        awards=[
            AwardDTO(
                award_info_id=1,
                name="蓝桥杯程序设计大赛（广东省赛）二等奖",
                award_time="2025-01-01",
            )
        ],
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Test local LaTeX template generation.")
    parser.add_argument(
        "template",
        nargs="?",
        default=str(DEFAULT_TEMPLATE),
        help="Template .tex file or template directory. Defaults to templates/resume/tech.tex.",
    )
    args = parser.parse_args()

    result = LatexTemplateAgent().generate_package(
        build_sample_resume(),
        template_path=Path(args.template),
        output_root=DEFAULT_OUTPUT_ROOT,
        package_name="test_resume_agent",
    )

    print(
        json.dumps(
            {
                "mainFileName": result.main_file_name,
                "packageDir": str(result.package_dir),
                "zipPath": str(result.zip_path),
                "warnings": result.warnings,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
