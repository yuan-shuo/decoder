export interface Symbol {
  id: number;
  name: string;
  qualified_name: string;
  type: string;
  file: string;
  line: number;
  end_line?: number;
  call_line?: number;
}

export interface CallerResult {
  symbol: Symbol;
  callers: Symbol[];
}

export interface CalleeResult {
  symbol: Symbol;
  callees: Symbol[];
}

export interface TreeNode {
  name: string;
  qualified_name: string;
  type: string;
  file: string;
  line: number;
  depth: number;
  is_conditional: boolean;
  condition: string | null;
  is_loop: boolean;
  is_try_block: boolean;
  children: TreeNode[];
}

export interface TraceResult {
  start: string;
  callers: TreeNode | null;
  callees: TreeNode | null;
}
