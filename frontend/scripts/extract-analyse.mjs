import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appPath = path.join(__dirname, '..', 'src', 'App.js');
const outDir = path.join(__dirname, '..', 'src', 'pages');
const outPath = path.join(outDir, 'AnalysePage.js');

const s = fs.readFileSync(appPath, 'utf8');
const start = s.indexOf('function AnalysePage()');
const end = s.indexOf('function LoginPage()');
if (start === -1 || end === -1 || end <= start) {
  console.error('Markers not found');
  process.exit(1);
}

let body = s.slice(start, end);
body = body.replace('function AnalysePage()', 'export default function AnalysePage()');
body = body.replace(/<BloomHeader\s*\/>/g, '<AppNav />');
body = body.replace(/<BloomHeader([^>]*)\/>/g, '<AppNav$1 />');

const header = `import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { API_BASE } from '../api';
import { authHeaders, getToken } from '../authStorage';
import { useTheme } from '../ThemeContext';
import { AppNav, Shell } from '../components/Layout';

`;

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(outPath, header + body, 'utf8');
console.log('Wrote', outPath);
