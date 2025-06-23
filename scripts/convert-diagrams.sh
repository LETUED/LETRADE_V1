#!/bin/bash

# 다이어그램 변환 스크립트
echo "📊 Converting Mermaid diagrams to PNG..."

# 출력 디렉터리 생성
mkdir -p diagrams

# Helper function to wrap raw mermaid with markdown
wrap_mermaid() {
    local input_file="$1"
    local temp_file="temp_wrapped_$(basename "$input_file")"
    
    echo "# $(basename "$input_file" .md)" > "$temp_file"
    echo "" >> "$temp_file"
    echo '```mermaid' >> "$temp_file"
    cat "$input_file" >> "$temp_file"
    echo '```' >> "$temp_file"
    
    echo "$temp_file"
}

# MVP 다이어그램들
echo "🔄 Converting MVP diagrams..."

if [[ -f "docs/mvp/자동 암호화폐 거래 시스템 컴포넌트 다이어그램.md" ]]; then
    temp_file=$(wrap_mermaid "docs/mvp/자동 암호화폐 거래 시스템 컴포넌트 다이어그램.md")
    mmdc -i "$temp_file" -o "diagrams/mvp_component_diagram.png" -t dark --backgroundColor transparent
    rm "$temp_file"
    echo "✅ Component diagram converted"
fi

if [[ -f "docs/mvp/자동 암호화폐 거래 시스템 UML 다이어그램.md" ]]; then
    temp_file=$(wrap_mermaid "docs/mvp/자동 암호화폐 거래 시스템 UML 다이어그램.md")
    mmdc -i "$temp_file" -o "diagrams/mvp_class_diagram.png" -t dark --backgroundColor transparent
    rm "$temp_file"
    echo "✅ UML class diagram converted"
fi

if [[ -f "docs/mvp/자동 암호화폐 거래 시스템 상태 다이어그램.md" ]]; then
    temp_file=$(wrap_mermaid "docs/mvp/자동 암호화폐 거래 시스템 상태 다이어그램.md")
    mmdc -i "$temp_file" -o "diagrams/mvp_state_diagram.png" -t dark --backgroundColor transparent
    rm "$temp_file"
    echo "✅ State diagram converted"
fi

# 시퀀스 다이어그램은 별도 처리 (문법 복잡성 때문에)
echo "⚠️  Sequence diagram requires manual syntax check"

# 고급 시스템 다이어그램들
echo "🔄 Converting advanced system diagrams..."

if [[ -f "docs/full-system/전체 시스템 클래스 다이어그램(고급 기능 포함).md" ]]; then
    temp_file=$(wrap_mermaid "docs/full-system/전체 시스템 클래스 다이어그램(고급 기능 포함).md")
    mmdc -i "$temp_file" -o "diagrams/full_system_class_diagram.png" -t dark --backgroundColor transparent
    rm "$temp_file"
    echo "✅ Full system class diagram converted"
fi

echo "🎉 Diagram conversion completed!"
echo "📁 Check the 'diagrams/' folder for generated PNG files."