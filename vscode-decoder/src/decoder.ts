import * as vscode from 'vscode';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as path from 'path';
import * as fs from 'fs';
import { Symbol, CallerResult, CalleeResult, TraceResult } from './types';

const execAsync = promisify(exec);

export class DecoderClient {
  private getPythonPath(): string {
    const config = vscode.workspace.getConfiguration('decoder');
    return config.get<string>('pythonPath', 'python');
  }

  private getWorkspacePath(): string {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    return workspaceFolder?.uri.fsPath || process.cwd();
  }

  async runCommand(args: string[]): Promise<string> {
    const pythonPath = this.getPythonPath();
    const cwd = this.getWorkspacePath();
    const command = `${pythonPath} -m decoder ${args.join(' ')}`;

    try {
      const { stdout } = await execAsync(command, { cwd });
      return stdout;
    } catch (error: unknown) {
      const err = error as { stderr?: string; message?: string; };
      throw new Error(err.stderr || err.message || 'Unknown error');
    }
  }

  async index(workspacePath: string): Promise<void> {
    await this.runCommand(['index', workspacePath, '--force']);
  }

  async hasIndex(workspacePath: string): Promise<boolean> {
    const indexPath = path.join(workspacePath, '.decoder', 'index.db');
    return fs.existsSync(indexPath);
  }

  async find(name: string): Promise<Symbol[]> {
    const output = await this.runCommand(['find', name, '--json']);
    return JSON.parse(output);
  }

  async getCallers(name: string): Promise<CallerResult[]> {
    const output = await this.runCommand(['callers', name, '--json']);
    return JSON.parse(output);
  }

  async getCallees(name: string): Promise<CalleeResult[]> {
    const output = await this.runCommand(['callees', name, '--json']);
    return JSON.parse(output);
  }

  async getStats(): Promise<{ files: number; symbols: number; edges: number; }> {
    const output = await this.runCommand(['stats', '--json']);
    return JSON.parse(output);
  }

  async trace(name: string, maxDepth: number = 10): Promise<TraceResult> {
    const output = await this.runCommand(['trace', name, '--depth', maxDepth.toString(), '--json']);
    return JSON.parse(output);
  }
}

export { Symbol, CallerResult, CalleeResult, TreeNode, TraceResult } from './types';
