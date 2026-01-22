import * as vscode from 'vscode';
import { CallTreeProvider, CallTreeItem } from './callTreeProvider';

export class TracePlayer {
  private isPlaying: boolean = false;
  private playInterval: NodeJS.Timeout | undefined;
  private currentDecoration: vscode.TextEditorDecorationType | undefined;

  constructor(
    private callTreeProvider: CallTreeProvider,
    private treeView: vscode.TreeView<CallTreeItem>
  ) { }

  async play(): Promise<void> {
    if (this.isPlaying) {
      return;
    }

    const items = this.callTreeProvider.getTraceItems();
    if (items.length === 0) {
      vscode.window.showWarningMessage('No trace to play. Use "Show Callers" or "Show Callees" first.');
      return;
    }

    this.isPlaying = true;
    vscode.commands.executeCommand('setContext', 'decoder.isPlaying', true);

    const config = vscode.workspace.getConfiguration('decoder');
    const speed = config.get<number>('playSpeed', 1500);

    await this.highlightCurrentStep();

    this.playInterval = setInterval(async () => {
      const currentIndex = this.callTreeProvider.getCurrentTraceIndex();
      const items = this.callTreeProvider.getTraceItems();

      if (currentIndex >= items.length - 1) {
        this.pause();
        this.callTreeProvider.setCurrentTraceIndex(0);
        vscode.window.showInformationMessage('Trace complete');
        return;
      }

      this.callTreeProvider.setCurrentTraceIndex(currentIndex + 1);
      await this.highlightCurrentStep();
    }, speed);
  }

  pause(): void {
    if (!this.isPlaying) {
      return;
    }

    this.isPlaying = false;
    vscode.commands.executeCommand('setContext', 'decoder.isPlaying', false);
    vscode.commands.executeCommand('setContext', 'decoder.isPaused', true);

    if (this.playInterval) {
      clearInterval(this.playInterval);
      this.playInterval = undefined;
    }

    vscode.window.setStatusBarMessage('Decoder: Paused', 2000);
  }

  stop(): void {
    this.isPlaying = false;
    vscode.commands.executeCommand('setContext', 'decoder.isPlaying', false);
    vscode.commands.executeCommand('setContext', 'decoder.isPaused', false);

    if (this.playInterval) {
      clearInterval(this.playInterval);
      this.playInterval = undefined;
    }

    this.clearHighlight();
  }

  async nextStep(): Promise<void> {
    const currentIndex = this.callTreeProvider.getCurrentTraceIndex();
    const items = this.callTreeProvider.getTraceItems();

    if (currentIndex < items.length - 1) {
      this.callTreeProvider.setCurrentTraceIndex(currentIndex + 1);
      await this.highlightCurrentStep();
    }
  }

  async prevStep(): Promise<void> {
    const currentIndex = this.callTreeProvider.getCurrentTraceIndex();

    if (currentIndex > 0) {
      this.callTreeProvider.setCurrentTraceIndex(currentIndex - 1);
      await this.highlightCurrentStep();
    }
  }

  private async highlightCurrentStep(): Promise<void> {
    const item = this.callTreeProvider.getCurrentTraceItem();
    if (!item || !item.filePath || !item.line) {
      return;
    }

    this.clearHighlight();

    try {
      await this.treeView.reveal(item, { select: true, focus: false, expand: true });
    } catch {
      // Item may not be visible in tree
    }

    const uri = vscode.Uri.file(item.filePath);
    try {
      const document = await vscode.workspace.openTextDocument(uri);
      const editor = await vscode.window.showTextDocument(document, {
        preview: true,
        preserveFocus: false
      });

      const line = item.line - 1;
      const position = new vscode.Position(line, 0);
      editor.selection = new vscode.Selection(position, position);
      editor.revealRange(
        new vscode.Range(position, position),
        vscode.TextEditorRevealType.InCenter
      );

      this.currentDecoration = vscode.window.createTextEditorDecorationType({
        backgroundColor: new vscode.ThemeColor('editor.findMatchHighlightBackground'),
        isWholeLine: true,
        borderWidth: '2px',
        borderStyle: 'solid',
        borderColor: new vscode.ThemeColor('editorWarning.foreground')
      });

      editor.setDecorations(this.currentDecoration, [
        new vscode.Range(line, 0, line, 0)
      ]);

      const currentIndex = this.callTreeProvider.getCurrentTraceIndex();
      const totalSteps = this.callTreeProvider.getTraceItems().length;
      vscode.window.setStatusBarMessage(
        `Decoder: Step ${currentIndex + 1}/${totalSteps} - ${item.symbol?.name || item.label}`,
        3000
      );

    } catch (error) {
      console.error('Failed to highlight step:', error);
    }
  }

  private clearHighlight(): void {
    if (this.currentDecoration) {
      this.currentDecoration.dispose();
      this.currentDecoration = undefined;
    }
  }
}
