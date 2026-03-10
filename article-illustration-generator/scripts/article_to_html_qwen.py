#!/usr/bin/env python3
"""
Article Illustration Generator - Qwen Wanx Version

This script generates illustrations for articles using Qwen Wanx (通义万相) API
and converts them into beautifully designed HTML pages.

Usage:
    python article_to_html_qwen.py <article_file> <api_key> [--images N]

Arguments:
    article_file    Path to the text article file
    api_key         Qwen (DashScope) API key
    --images N      Number of images to generate (default: 5)
"""

import os
import sys
import time
import io
import argparse
from dashscope import ImageSynthesis
from PIL import Image
import base64

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# --- Configuration ---
DEFAULT_IMAGE_COUNT = 5
DEFAULT_MODEL = "wanx-v1"

# Get script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
TEMPLATE_FILE = os.path.join(SKILL_DIR, "assets", "template.html")

# Output directory in current working directory
OUTPUT_DIR = os.path.join(os.getcwd(), "output")


def generate_scene_prompts(paragraphs, title, num_images):
    """
    Generate image prompts based on article paragraphs.
    Creates prompts in both Chinese (for Qwen) and English.
    """
    print(f"\n🎨 正在生成 {num_images} 个场景描述...")

    scenes = []

    # First image: overall atmosphere (header)
    scenes.append({
        "prompt": f"一幅温暖治愈的周末聚餐场景，柔和的黄色灯光，几个好朋友围坐在餐桌旁，桌上摆着热气腾腾的美食，温馨的家庭氛围，水彩画风格，柔和的光影",
        "caption": f"《{title}》"
    })

    # Distribute remaining images across paragraphs
    if num_images > 1 and len(paragraphs) > 0:
        # Select paragraphs evenly distributed throughout the article
        step = max(1, len(paragraphs) // (num_images - 1))
        selected_indices = [i * step for i in range(num_images - 1)]

        for idx, para_idx in enumerate(selected_indices, 1):
            if para_idx < len(paragraphs):
                paragraph = paragraphs[para_idx]

                # Extract key visual elements from paragraph
                excerpt = paragraph[:80] if len(paragraph) > 80 else paragraph

                # Create Chinese prompt (Qwen works better with Chinese)
                scenes.append({
                    "prompt": f"一幅温馨治愈的插画，描绘周末和朋友聚餐的美好时光：{excerpt}，温暖的色调，柔和的光影，水彩画风格，充满生活气息",
                    "caption": f"《{title}》插图 {idx}"
                })

    print(f"✓ 已生成 {len(scenes)} 个场景描述")
    return scenes


def generate_image(api_key, prompt, filename, size="1024*1024"):
    """
    Generates an image using Qwen Wanx API and saves it to filename.
    """
    print(f"🖼️  正在生成图片: {filename}...")
    print(f"   Prompt: {prompt[:60]}...")

    try:
        response = ImageSynthesis.call(
            model=DEFAULT_MODEL,
            api_key=api_key,
            prompt=prompt,
            size=size,
            n=1
        )

        if response.status_code == 200:
            # Get image data from response
            image_url = response.output.results[0].url

            # Download image from URL
            import requests
            img_response = requests.get(image_url)

            if img_response.status_code == 200:
                img = Image.open(io.BytesIO(img_response.content))

                # Ensure output directory exists
                os.makedirs(OUTPUT_DIR, exist_ok=True)

                output_path = os.path.join(OUTPUT_DIR, filename)
                img.save(output_path)
                print(f"✓ 已保存到 {output_path}")
                return True
            else:
                print(f"✗ 下载图片失败: HTTP {img_response.status_code}")
                return False
        else:
            print(f"✗ API 调用失败: {response.code} - {response.message}")
            return False

    except Exception as e:
        print(f"✗ 生成 {filename} 时出错: {e}")
        return False


def read_article(article_file):
    """Read and parse the article text from file."""
    with open(article_file, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = [line.strip() for line in content.split('\n') if line.strip()]

    if len(lines) < 1:
        raise ValueError("文章格式错误：至少需要标题")

    # First line is title (remove markdown heading if present)
    title = lines[0].replace('#', '').strip()

    # Extract paragraphs (skip empty lines and hashtags)
    paragraphs = []
    for line in lines[1:]:
        # Skip hashtag lines (social media tags)
        if line.startswith('#') or line.startswith('##'):
            continue
        if line.strip():
            paragraphs.append(line)

    return title, paragraphs, content


def create_html(title, paragraphs, image_files):
    """Create HTML file with article content and images."""

    # Read template
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        template = f.read()

    # Update header background image FIRST (before replacing title)
    # The template has: url('故都的秋4.png')
    header_image = image_files[0]["filename"]
    html = template.replace("url('故都的秋4.png')", f"url('{header_image}')")

    # Then replace title and author (use generic author for now)
    html = html.replace("故都的秋", title)
    html = html.replace("郁达夫", "原创")

    # Build article content with images
    article_content = ""

    # Calculate how to distribute images throughout the article
    num_paragraphs = len(paragraphs)
    num_images = len(image_files) - 1  # Exclude header image

    if num_images > 0:
        # Distribute images evenly throughout the article
        paragraphs_per_image = max(1, num_paragraphs // (num_images + 1))
    else:
        paragraphs_per_image = num_paragraphs

    image_index = 1  # Start from 1 (0 is header)

    for i, paragraph in enumerate(paragraphs):
        # Add paragraph
        article_content += f'            <p>{paragraph}</p>\n'

        # Add image after certain number of paragraphs
        if image_index < len(image_files) and (i + 1) % paragraphs_per_image == 0 and i < num_paragraphs - 1:
            article_content += f'''            <div class="article-image">
                <img src="{image_files[image_index]["filename"]}" alt="{image_files[image_index]["caption"]}">
                <span class="image-caption">{image_files[image_index]["caption"]}</span>
            </div>

'''
            image_index += 1

    # Replace the article section in template
    start_marker = '<article>'
    end_marker = '</article>'
    start_idx = html.find(start_marker)
    end_idx = html.find(end_marker)

    if start_idx != -1 and end_idx != -1:
        html = html[:start_idx + len(start_marker)] + '\n' + article_content + '        ' + html[end_idx:]

    # Update footer
    html = html.replace("故都的秋 - 图文排版", f"{title} - 图文排版")

    # Write output HTML
    # Sanitize filename
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    output_html = os.path.join(OUTPUT_DIR, f"{safe_title}.html")

    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✓ HTML文件已生成: {output_html}")
    return output_html


def main():
    """Main processing function."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='使用通义万相生成文章插图并转换为HTML',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('article_file', help='文章文件路径 (.txt)')
    parser.add_argument('api_key', help='通义千问 API Key')
    parser.add_argument('--images', type=int, default=DEFAULT_IMAGE_COUNT,
                        help=f'生成的图片数量 (默认: {DEFAULT_IMAGE_COUNT})')
    parser.add_argument('--size', default="1024*1024",
                        help='图片尺寸 (默认: 1024*1024)')

    args = parser.parse_args()

    # Check if article file exists
    if not os.path.exists(args.article_file):
        print(f"错误: 文章文件不存在: {args.article_file}")
        return 1

    # Check if template exists
    if not os.path.exists(TEMPLATE_FILE):
        print(f"错误: 模板文件不存在: {TEMPLATE_FILE}")
        print("请确保 assets/template.html 文件存在")
        return 1

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("周末盲盒饭局 - 文章插图生成器")
    print("Powered by Qwen Wanx (通义万相)")
    print("=" * 60)

    # Read article
    print(f"\n1️⃣  读取文章: {args.article_file}")
    try:
        title, paragraphs, full_text = read_article(args.article_file)
        print(f"   标题: {title}")
        print(f"   段落数: {len(paragraphs)}")
    except Exception as e:
        print(f"错误: 读取文章失败: {e}")
        return 1

    # Generate scene prompts based on paragraphs
    scenes = generate_scene_prompts(paragraphs, title, args.images)

    # Prepare image filenames
    base_name = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    for i, scene in enumerate(scenes):
        if i == 0:
            scene['filename'] = f"{base_name}_header.png"
        else:
            scene['filename'] = f"{base_name}_{i}.png"

    # Generate images
    print(f"\n2️⃣  生成 {len(scenes)} 张插图...")
    print(f"   API: Qwen Wanx (通义万相)")
    print(f"   尺寸: {args.size}")

    generated_images = []
    for i, scene in enumerate(scenes, 1):
        print(f"\n   [{i}/{len(scenes)}] {scene['caption']}")
        success = generate_image(
            args.api_key,
            scene["prompt"],
            scene["filename"],
            args.size
        )
        if success:
            generated_images.append(scene)
        # Rate limiting - wait between requests
        if i < len(scenes):
            print(f"   ⏳ 等待 3 秒...")
            time.sleep(3)

    if not generated_images:
        print("\n错误: 没有成功生成任何图片")
        return 1

    print(f"\n   ✓ 成功生成 {len(generated_images)}/{len(scenes)} 张图片")

    # Create HTML
    print("\n3️⃣  生成 HTML 文件...")
    try:
        output_file = create_html(title, paragraphs, generated_images)
    except Exception as e:
        print(f"错误: 生成HTML失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n" + "=" * 60)
    print("✓ 处理完成!")
    print(f"📁 输出目录: {OUTPUT_DIR}/")
    print(f"📄 HTML文件: {output_file}")
    print(f"🖼️  图片文件: {len(generated_images)} 张")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
