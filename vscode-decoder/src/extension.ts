import * as vscode from 'vscode';
import { DecoderClient } from './decoder';
import { CallTreeProvider, CallTreeItem } from './callTreeProvider';
import { TracePlayer } from './tracePlayer';

let decoderClient: DecoderClient;
let callTreeProvider: CallTreeProvider;
let tracePlayer: TracePlayer;
let treeView: vscode.TreeView<CallTreeItem>;

export function activate(context: vscode.ExtensionContext) {

  decoderClient = new DecoderClient();

  callTreeProvider = new CallTreeProvider(decoderClient);
  treeView = vscode.window.createTreeView('decoderCallTree', {
    treeDataProvider: callTreeProvider
  });

  tracePlayer = new TracePlayer(callTreeProvider, treeView);

  context.subscriptions.push(
    treeView,
    vscode.commands.registerCommand('decoder.index', indexWorkspace),
    vscode.commands.registerCommand('decoder.showCallers', showCallers),
    vscode.commands.registerCommand('decoder.showCallees', showCallees),
    vscode.commands.registerCommand('decoder.trace', showTrace),
    vscode.commands.registerCommand('decoder.playTrace', () => tracePlayer.play()),
    vscode.commands.registerCommand('decoder.pauseTrace', () => tracePlayer.pause()),
    vscode.commands.registerCommand('decoder.stopTrace', () => tracePlayer.stop()),
    vscode.commands.registerCommand('decoder.nextStep', () => tracePlayer.nextStep()),
    vscode.commands.registerCommand('decoder.prevStep', () => tracePlayer.prevStep()),
    vscode.commands.registerCommand('decoder.goToSymbol', goToSymbol)
  );

  checkAndPromptIndex();
}

async function indexWorkspace() {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
  if (!workspaceFolder) {
    vscode.window.showErrorMessage('No workspace folder open');
    return;
  }

  await vscode.window.withProgress({
    location: vscode.ProgressLocation.Notification,
    title: 'Decoder: Indexing workspace...',
    cancellable: false
  }, async () => {
    try {
      await decoderClient.index(workspaceFolder.uri.fsPath);
      vscode.window.showInformationMessage('Decoder: Indexing complete');
    } catch (error) {
      vscode.window.showErrorMessage(`Decoder: Indexing failed - ${error}`);
    }
  });
}

async function showCallers() {
  const symbol = await getSymbolAtCursor();
  if (!symbol) {
    vscode.window.showWarningMessage('No symbol found at cursor');
    return;
  }

  const currentFile = vscode.window.activeTextEditor?.document.uri.fsPath;

  try {
    const results = await decoderClient.getCallers(symbol);

    if (results.length === 0) {
      vscode.window.showInformationMessage(`No callers found for ${symbol}`);
      return;
    }

    let result = results.find(r => r.symbol.file === currentFile);
    if (!result) {
      result = results.find(r => r.callers.length > 0) || results[0];
    }

    if (result.callers.length === 0) {
      vscode.window.showInformationMessage(`No callers found for ${symbol}`);
      return;
    }
    callTreeProvider.showCallers(result);
  } catch (error) {
    console.error('Decoder error:', error);
    vscode.window.showErrorMessage(`Failed to get callers: ${error}`);
  }
}

async function showCallees() {
  const symbol = await getSymbolAtCursor();
  if (!symbol) {
    vscode.window.showWarningMessage('No symbol found at cursor');
    return;
  }

  const currentFile = vscode.window.activeTextEditor?.document.uri.fsPath;

  try {
    const results = await decoderClient.getCallees(symbol);
    if (results.length === 0) {
      vscode.window.showInformationMessage(`No callees found for ${symbol}`);
      return;
    }

    let result = results.find(r => r.symbol.file === currentFile);
    if (!result) {
      result = results.find(r => r.callees.length > 0) || results[0];
    }

    if (result.callees.length === 0) {
      vscode.window.showInformationMessage(`No callees found for ${symbol}`);
      return;
    }
    callTreeProvider.showCallees(result);
  } catch (error) {
    vscode.window.showErrorMessage(`Failed to get callees: ${error}`);
  }
}

async function showTrace() {
  const symbol = await getSymbolAtCursor();
  if (!symbol) {
    vscode.window.showWarningMessage('No symbol found at cursor');
    return;
  }

  try {
    const result = await decoderClient.trace(symbol);
    const hasCallers = result.callers && result.callers.children.length > 0;
    const hasCallees = result.callees && result.callees.children.length > 0;
    if (!hasCallers && !hasCallees) {
      vscode.window.showInformationMessage(`No trace found for ${symbol}`);
      return;
    }
    callTreeProvider.showTrace(result);
    const callerCount = result.callers?.children.length || 0;
    const calleeCount = result.callees?.children.length || 0;
    vscode.window.showInformationMessage(
      `Found ${callerCount} callers and ${calleeCount} callees.`
    );
  } catch (error) {
    vscode.window.showErrorMessage(`Failed to trace: ${error}`);
  }
}

async function getSymbolAtCursor(): Promise<string | undefined> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    return undefined;
  }

  const document = editor.document;
  const position = editor.selection.active;
  const wordRange = document.getWordRangeAtPosition(position);

  if (!wordRange) {
    return undefined;
  }

  return document.getText(wordRange);
}

async function goToSymbol(item: CallTreeItem) {
  if (!item.filePath || !item.line) {
    return;
  }

  const uri = vscode.Uri.file(item.filePath);
  const document = await vscode.workspace.openTextDocument(uri);
  const editor = await vscode.window.showTextDocument(document);

  const position = new vscode.Position(item.line - 1, 0);
  editor.selection = new vscode.Selection(position, position);
  editor.revealRange(new vscode.Range(position, position), vscode.TextEditorRevealType.InCenter);

  const decoration = vscode.window.createTextEditorDecorationType({
    backgroundColor: new vscode.ThemeColor('editor.findMatchHighlightBackground'),
    isWholeLine: true
  });

  editor.setDecorations(decoration, [new vscode.Range(position, position)]);

  setTimeout(() => {
    decoration.dispose();
  }, 2000);
}

async function checkAndPromptIndex() {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
  if (!workspaceFolder) {
    return;
  }

  const hasIndex = await decoderClient.hasIndex(workspaceFolder.uri.fsPath);
  if (!hasIndex) {
    const action = await vscode.window.showInformationMessage(
      'Decoder: No index found. Index this workspace?',
      'Index Now',
      'Later'
    );
    if (action === 'Index Now') {
      await indexWorkspace();
    }
  }
}

export function deactivate() {
  tracePlayer?.stop();
}
