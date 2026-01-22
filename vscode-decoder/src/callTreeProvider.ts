import * as vscode from 'vscode';
import { DecoderClient } from './decoder';
import { Symbol, CallerResult, CalleeResult, TraceResult, TreeNode } from './types';

export class CallTreeItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly collapsibleState: vscode.TreeItemCollapsibleState,
    public readonly symbol?: Symbol,
    public readonly filePath?: string,
    public readonly line?: number,
    public readonly isRoot: boolean = false,
    public readonly direction: 'callers' | 'callees' = 'callees'
  ) {
    super(label, collapsibleState);

    if (symbol) {
      this.description = `${symbol.type}`;
      this.tooltip = `${symbol.qualified_name}\n${symbol.file}:${symbol.line}`;

      const iconMap: Record<string, string> = {
        'function': 'symbol-function',
        'method': 'symbol-method',
        'class': 'symbol-class'
      };
      this.iconPath = new vscode.ThemeIcon(iconMap[symbol.type] || 'symbol-misc');

      this.command = {
        command: 'decoder.goToSymbol',
        title: 'Go to Symbol',
        arguments: [this]
      };
    }

    if (isRoot) {
      this.iconPath = new vscode.ThemeIcon(
        direction === 'callers' ? 'arrow-left' : 'arrow-right'
      );
    }
  }
}

export class CallTreeProvider implements vscode.TreeDataProvider<CallTreeItem> {
  private _onDidChangeTreeData: vscode.EventEmitter<CallTreeItem | undefined | null | void> =
    new vscode.EventEmitter<CallTreeItem | undefined | null | void>();
  readonly onDidChangeTreeData: vscode.Event<CallTreeItem | undefined | null | void> =
    this._onDidChangeTreeData.event;

  private rootItems: CallTreeItem[] = [];
  private childrenMap: Map<CallTreeItem, CallTreeItem[]> = new Map();
  private parentMap: Map<CallTreeItem, CallTreeItem> = new Map();

  private traceItems: CallTreeItem[] = [];
  private currentTraceIndex: number = 0;

  constructor(private decoderClient: DecoderClient) { }

  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: CallTreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: CallTreeItem): Thenable<CallTreeItem[]> {
    if (!element) {
      return Promise.resolve(this.rootItems);
    }
    return Promise.resolve(this.childrenMap.get(element) || []);
  }

  getParent(element: CallTreeItem): CallTreeItem | undefined {
    return this.parentMap.get(element);
  }

  showCallers(result: CallerResult): void {
    this.rootItems = [];
    this.childrenMap.clear();
    this.parentMap.clear();
    this.traceItems = [];

    const rootItem = new CallTreeItem(
      `${result.symbol.name} ← callers`,
      vscode.TreeItemCollapsibleState.Expanded,
      result.symbol,
      result.symbol.file,
      result.symbol.line,
      true,
      'callers'
    );
    this.rootItems.push(rootItem);

    const children: CallTreeItem[] = result.callers.map(caller => {
      const item = new CallTreeItem(
        caller.name,
        vscode.TreeItemCollapsibleState.None,
        caller,
        caller.file,
        caller.call_line || caller.line
      );
      this.traceItems.push(item);
      return item;
    });

    this.childrenMap.set(rootItem, children);
    children.forEach(child => this.parentMap.set(child, rootItem));
    this.currentTraceIndex = 0;
    this.refresh();
  }

  showCallees(result: CalleeResult): void {
    this.rootItems = [];
    this.childrenMap.clear();
    this.parentMap.clear();
    this.traceItems = [];

    const rootItem = new CallTreeItem(
      `${result.symbol.name} → callees`,
      vscode.TreeItemCollapsibleState.Expanded,
      result.symbol,
      result.symbol.file,
      result.symbol.line,
      true,
      'callees'
    );
    this.rootItems.push(rootItem);
    this.traceItems.push(rootItem);

    const children: CallTreeItem[] = result.callees.map(callee => {
      const item = new CallTreeItem(
        callee.name,
        vscode.TreeItemCollapsibleState.None,
        callee,
        callee.file,
        callee.call_line || callee.line
      );
      this.traceItems.push(item);
      return item;
    });

    this.childrenMap.set(rootItem, children);
    children.forEach(child => this.parentMap.set(child, rootItem));
    this.currentTraceIndex = 0;
    this.refresh();
  }

  showTrace(result: TraceResult): void {
    this.rootItems = [];
    this.childrenMap.clear();
    this.parentMap.clear();
    this.traceItems = [];

    const selectedName = result.start.split('.').pop() || result.start;

    const formatContext = (node: TreeNode): string => {
      const parts: string[] = [];
      if (node.is_conditional) {
        if (node.condition && node.condition.length <= 20) {
          parts.push(`if ${node.condition}`);
        } else {
          parts.push('conditional');
        }
      }
      if (node.is_loop) {
        parts.push('loop');
      }
      if (node.is_try_block) {
        parts.push('try');
      }
      return parts.length > 0 ? ` [${parts.join(', ')}]` : '';
    };

    const createItem = (node: TreeNode, direction: 'caller' | 'callee' | 'selected'): CallTreeItem => {
      const symbol: Symbol = {
        id: 0,
        name: node.name,
        qualified_name: node.qualified_name,
        type: node.type,
        file: node.file,
        line: node.line,
      };

      const ctx = formatContext(node);
      const label = `${node.name}${ctx}`;

      const item = new CallTreeItem(
        label,
        node.children.length > 0 ? vscode.TreeItemCollapsibleState.Expanded : vscode.TreeItemCollapsibleState.None,
        symbol,
        node.file,
        node.line
      );

      if (direction === 'selected') {
        item.iconPath = new vscode.ThemeIcon('debug-stackframe-focused');
      } else if (direction === 'caller') {
        item.iconPath = new vscode.ThemeIcon('arrow-up');
      } else if (node.is_conditional || node.is_loop || node.is_try_block) {
        item.iconPath = new vscode.ThemeIcon('arrow-down', new vscode.ThemeColor('editorWarning.foreground'));
      } else {
        item.iconPath = new vscode.ThemeIcon('arrow-down');
      }

      return item;
    };

    const buildTreeItems = (node: TreeNode, direction: 'caller' | 'callee', parent?: CallTreeItem): CallTreeItem[] => {
      const items: CallTreeItem[] = [];
      for (const child of node.children) {
        const item = createItem(child, direction);
        items.push(item);
        this.traceItems.push(item);
        if (parent) {
          this.parentMap.set(item, parent);
        }

        if (child.children.length > 0) {
          const childItems = buildTreeItems(child, direction, item);
          this.childrenMap.set(item, childItems);
        }
      }
      return items;
    };

    const sections: CallTreeItem[] = [];

    if (result.callers && result.callers.children.length > 0) {
      const callersRoot = new CallTreeItem(
        'Callers',
        vscode.TreeItemCollapsibleState.Expanded,
        undefined, undefined, undefined, true, 'callers'
      );
      sections.push(callersRoot);
      const callerItems = buildTreeItems(result.callers, 'caller', callersRoot);
      this.childrenMap.set(callersRoot, callerItems);
    }

    if (result.callees) {
      const selectedItem = new CallTreeItem(
        `▶ ${selectedName} ◀`,
        vscode.TreeItemCollapsibleState.None,
        {
          id: 0,
          name: result.callees.name,
          qualified_name: result.callees.qualified_name,
          type: result.callees.type,
          file: result.callees.file,
          line: result.callees.line,
        },
        result.callees.file,
        result.callees.line
      );
      selectedItem.iconPath = new vscode.ThemeIcon('debug-stackframe-focused');
      sections.push(selectedItem);
      this.traceItems.push(selectedItem);
    }

    if (result.callees && result.callees.children.length > 0) {
      const calleesRoot = new CallTreeItem(
        'Callees',
        vscode.TreeItemCollapsibleState.Expanded,
        undefined, undefined, undefined, true, 'callees'
      );
      sections.push(calleesRoot);
      const calleeItems = buildTreeItems(result.callees, 'callee', calleesRoot);
      this.childrenMap.set(calleesRoot, calleeItems);
    }

    this.rootItems = sections;
    this.currentTraceIndex = 0;
    this.refresh();
  }

  getTraceItems(): CallTreeItem[] {
    return this.traceItems;
  }

  getCurrentTraceIndex(): number {
    return this.currentTraceIndex;
  }

  setCurrentTraceIndex(index: number): void {
    if (index >= 0 && index < this.traceItems.length) {
      this.currentTraceIndex = index;
    }
  }

  getCurrentTraceItem(): CallTreeItem | undefined {
    return this.traceItems[this.currentTraceIndex];
  }
}
