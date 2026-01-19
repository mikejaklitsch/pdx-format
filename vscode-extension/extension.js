const vscode = require('vscode');
const { spawn } = require('child_process');
const path = require('path');
const os = require('os');

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    // Register formatter for paradox files
    const formatter = vscode.languages.registerDocumentFormattingEditProvider(
        [
            { scheme: 'file', language: 'paradox' },
            { scheme: 'file', pattern: '**/*.txt' },
            { scheme: 'file', pattern: '**/*.gui' }
        ],
        {
            provideDocumentFormattingEdits(document) {
                return formatDocument(document);
            }
        }
    );

    // Register formatter for range (selection)
    const rangeFormatter = vscode.languages.registerDocumentRangeFormattingEditProvider(
        [
            { scheme: 'file', language: 'paradox' },
            { scheme: 'file', pattern: '**/*.txt' },
            { scheme: 'file', pattern: '**/*.gui' }
        ],
        {
            provideDocumentRangeFormattingEdits(document, range) {
                // For simplicity, format the whole document
                return formatDocument(document);
            }
        }
    );

    context.subscriptions.push(formatter, rangeFormatter);

    console.log('PDX Format extension activated');
}

function getFormatterPath() {
    const config = vscode.workspace.getConfiguration('pdxFormat');
    const customPath = config.get('formatterPath');

    if (customPath && customPath.trim()) {
        return customPath;
    }

    // Default path
    return path.join(os.homedir(), '.local', 'bin', 'pdx-format');
}

/**
 * Format a document using pdx-format CLI
 * @param {vscode.TextDocument} document
 * @returns {Promise<vscode.TextEdit[]>}
 */
function formatDocument(document) {
    return new Promise((resolve, reject) => {
        const formatterPath = getFormatterPath();
        const originalText = document.getText();

        // Spawn pdx-format with stdin
        const proc = spawn(formatterPath, ['-'], {
            stdio: ['pipe', 'pipe', 'pipe']
        });

        let stdout = '';
        let stderr = '';

        proc.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        proc.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        proc.on('close', (code) => {
            if (code !== 0) {
                console.error('pdx-format error:', stderr);
                vscode.window.showErrorMessage(`PDX Format error: ${stderr || 'Unknown error'}`);
                resolve([]);
                return;
            }

            if (stdout === originalText) {
                // No changes needed
                resolve([]);
                return;
            }

            // Create a full document replacement edit
            const fullRange = new vscode.Range(
                document.positionAt(0),
                document.positionAt(originalText.length)
            );

            resolve([vscode.TextEdit.replace(fullRange, stdout)]);
        });

        proc.on('error', (err) => {
            console.error('Failed to run pdx-format:', err);
            vscode.window.showErrorMessage(`Failed to run pdx-format: ${err.message}`);
            resolve([]);
        });

        // Write document content to stdin
        proc.stdin.write(originalText);
        proc.stdin.end();
    });
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
};
