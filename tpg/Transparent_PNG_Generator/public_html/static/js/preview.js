document.addEventListener('DOMContentLoaded', function() {
    // 要素の取得
    const textInput = document.getElementById('text');
    const fontSizeInput = document.getElementById('fontSize');
    const colorInput = document.getElementById('color');
    const fontInput = document.getElementById('font');
    const lineHeightInput = document.getElementById('lineHeight');
    const lineHeightValue = document.getElementById('lineHeightValue');
    const previewText = document.getElementById('previewText');
    const charCountContainer = document.querySelector('.form-text[data-text]');
    const form = document.getElementById('textForm');
    const fontUpload = document.getElementById('fontUpload');
    const uploadFontBtn = document.getElementById('uploadFontBtn');
    const savedColorsContainer = document.getElementById('savedColors');
    const generateBtn = document.querySelector('button[type="submit"]');

    // CSRFトークンの取得
    const csrfToken = document.querySelector('input[name="csrf_token"]').value;

    // エラーチェック
    if (!previewText) {
        console.error('Preview text element not found');
        return;
    }

    // 翻訳テキストの取得
    const defaultPreviewText = previewText.dataset.defaultText;
    const charsRemainingText = charCountContainer?.dataset.text || 'Characters remaining';
    const MAX_LENGTH = 100;

    // エラー表示関数を修正
    function showError(message) {
        // 既存のエラーメッセージを削除
        const existingError = form.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }

        // 新しいエラーメッセージを作成
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;

        // エラーメッセージをフォームの先頭に追加
        form.insertBefore(errorDiv, form.firstChild);

        // 3秒後にエラーメッセージを消す
        setTimeout(() => {
            errorDiv.classList.add('fadeOut');
            setTimeout(() => errorDiv.remove(), 300);
        }, 3000);
    }

    // テキスト入力の制限とカウント更新
    function updateCharCount() {
        const text = textInput.value;
        const remainingChars = MAX_LENGTH - text.length;

        // 文字数が制限を超えた場合
        if (text.length > MAX_LENGTH) {
            textInput.value = text.substring(0, MAX_LENGTH);
            showError('テキストが最大文字数（100文字）を超えています');
            generateBtn.disabled = true;
        } else {
            generateBtn.disabled = false;
        }

        // 残り文字数の表示を更新
        if (charCountContainer) {
            charCountContainer.textContent = `${charsRemainingText}: ${Math.max(0, remainingChars)}`;
        }

        updatePreview();
    }

    // カラーフォーマットの保存・読み込みの関数
    function saveColorFormat(color) {
        let savedColors = JSON.parse(localStorage.getItem('savedColors') || '[]');
        savedColors = savedColors.filter(c => c !== color);
        savedColors.unshift(color);
        savedColors = savedColors.slice(0, 3);
        localStorage.setItem('savedColors', JSON.stringify(savedColors));
        updateSavedColorsUI();
    }

    function loadColorFormat() {
        const savedColors = JSON.parse(localStorage.getItem('savedColors') || '[]');
        updateSavedColorsUI();
        if (savedColors.length > 0) {
            colorInput.value = savedColors[0];
            updatePreview();
        }
    }

    function updateSavedColorsUI() {
        const savedColors = JSON.parse(localStorage.getItem('savedColors') || '[]');
        savedColorsContainer.innerHTML = '';
        savedColors.forEach(color => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'btn btn-sm saved-color-btn';
            button.style.backgroundColor = color;
            button.title = color;
            button.addEventListener('click', () => {
                colorInput.value = color;
                updatePreview();
            });
            savedColorsContainer.appendChild(button);
        });
    }

    // 保存された色を読み込む
    loadColorFormat();

    // テキスト入力の検証
    function validateText(text) {
        if (!text) {
            throw new Error('テキストを入力してください');
        }
        if (text.length > MAX_LENGTH) {
            throw new Error('テキストが最大文字数（100文字）を超えています');
        }
        return text;
    }

    // プレビュー更新関数
    function updatePreview() {
        try {
            const text = textInput.value || defaultPreviewText;
            validateText(text);

            const fontSize = fontSizeInput.value + 'px';
            const color = colorInput.value;
            const font = fontInput.value;
            const lineHeight = lineHeightInput.value;

            // プレビューのスタイル更新
            previewText.style.fontSize = fontSize;
            previewText.style.lineHeight = lineHeight;
            previewText.style.color = color;
            previewText.innerHTML = text.replace(/\n/g, '<br>');

            // フォントの設定
            if (font.endsWith('.ttf') || font.endsWith('.otf') || font.endsWith('.ttc')) {
                const fontFamilyName = `custom-${font.split('.')[0]}`;
                previewText.style.fontFamily = `${fontFamilyName}, sans-serif`;
            } else {
                previewText.style.fontFamily = font;
            }

            // 行間値の表示を更新
            if (lineHeightValue) {
                lineHeightValue.textContent = lineHeight;
            }

        } catch (error) {
            console.error('Preview update error:', error);
            if (error.message) {
                showError(error.message);
            }
        }
    }

    // イベントリスナーの設定
    function setupEventListeners() {
        // テキスト入力のイベント
        textInput?.addEventListener('input', updateCharCount);
        textInput?.addEventListener('paste', (e) => {
            setTimeout(updateCharCount, 0);
        });

        // その他の入力イベント
        fontSizeInput?.addEventListener('input', updatePreview);
        colorInput?.addEventListener('input', updatePreview);
        fontInput?.addEventListener('change', updatePreview);
        lineHeightInput?.addEventListener('input', updatePreview);

        // カラー保存機能
        colorInput?.addEventListener('change', function() {
            updatePreview();
            saveColorFormat(colorInput.value);
        });
    }

    // イベントリスナーの設定を実行
    setupEventListeners();

    // フォントアップロード処理
    uploadFontBtn.addEventListener('click', async function() {
        const file = fontUpload.files[0];
        if (!file) {
            showError('フォントファイルが選択されていません');
            return;
        }

        if (file.size > 10 * 1024 * 1024) {  // 10MB制限に修正
            showError('ファイルサイズが大きすぎます（最大10MB）');
            return;
        }

        const formData = new FormData();
        formData.append('font', file);
        formData.append('csrf_token', csrfToken);

        try {
            uploadFontBtn.disabled = true;
            const response = await fetch('/upload-font', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error);
            }

            // カスタムフォントのロード
            const fontFamilyName = `custom-${data.fontName.split('.')[0]}`;
            const fontFace = new FontFace(fontFamilyName, `url(/fonts/${data.fontName})`);

            // フォントをロードしてドキュメントに追加
            await fontFace.load();
            document.fonts.add(fontFace);

            // 新しいフォントオプションを追加
            const option = document.createElement('option');
            option.value = data.fontName;
            const customPrefix = document.documentElement.lang === 'ja' ? 'カスタム' : 'Custom';
            option.textContent = `${customPrefix}: ${data.fontName.split('.')[0]}`;
            fontInput.appendChild(option);

            // 新しいフォントを選択
            fontInput.value = data.fontName;

            // プレビューを更新
            updatePreview();

        } catch (error) {
            console.error('Font upload error:', error);
            showError(error.message);
        } finally {
            uploadFontBtn.disabled = false;
            fontUpload.value = '';
        }
    });

    // フォーム送信処理
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        try {
            // 送信前の入力値検証
            validateText(textInput.value);

            const formData = new FormData(form);
            const response = await fetch('/generate', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error);
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `text_${new Date().getTime()}.png`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();

        } catch (error) {
            console.error('Image generation error:', error);
            showError(error.message);
        }
    });

    // 初期化
    updateCharCount();
});