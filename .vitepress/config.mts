import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineConfig, type DefaultTheme } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

const root = resolve(import.meta.dirname, '..')

/** 侧边栏条目文字：取正文一级标题 */
function itemText(file: string): string {
  const raw = readFileSync(resolve(root, file), 'utf-8')
  return raw.match(/^#\s+(.+)$/m)?.[1] ?? file.replace(/\.md$/, '')
}

/** 章节按 chNN 编号排序，README（part 概览）排在最前 */
function chapterOrder(a: string, b: string): number {
  const num = (f: string) => Number(/ch(\d+)/.exec(f)?.[1] ?? -1)
  const [x, y] = [num(a), num(b)]
  if (x !== y) return x - y
  return a.localeCompare(b)
}

/** 全书按 part-N 编号排序 */
function partOrder(a: string, b: string): number {
  return Number(/part-(\d+)/.exec(a)?.[1] ?? 0) - Number(/part-(\d+)/.exec(b)?.[1] ?? 0)
}

/** 一个 part 目录 -> 侧边栏分组 */
function partGroup(dir: string): DefaultTheme.SidebarItem {
  const files = readdirSync(resolve(root, dir)).filter((f) => f.endsWith('.md'))
  const overview = files.filter((f) => f === 'README.md')
  const chapters = files.filter((f) => f !== 'README.md').sort(chapterOrder)

  return {
    text: itemText(`${dir}/README.md`).replace(/^Part\s*\d+\s*/, ''),
    collapsed: false,
    items: [
      ...overview.map(() => ({ text: '本部分概览', link: `/${dir}/` })),
      ...chapters.map((f) => ({
        text: itemText(`${dir}/${f}`),
        link: `/${dir}/${f.replace(/\.md$/, '')}`,
      })),
    ],
  }
}

const sidebar: DefaultTheme.SidebarItem[] = readdirSync(root)
  .filter((d) => /^part-\d/.test(d))
  .sort(partOrder)
  .map(partGroup)

/** 本地搜索默认按空白分词，中文整段会被当作一个词，这里退化为字粒度切分 */
function tokenize(text: string): string[] {
  const tokens: string[] = []
  for (const part of text.split(/[\s\n\r#%*,=/:;?[\]{}()&+\-!'"$·、，。：；？！（）【】《》…—]+/)) {
    if (!part) continue
    if (/[一-龥]/.test(part)) {
      tokens.push(part, ...part.split(''))
    } else {
      tokens.push(part)
    }
  }
  return tokens
}

export default withMermaid(
  defineConfig({
    title: 'Agent 原理及实践',
    description: '一本从原理到实践的中文技术书籍，面向有编程基础但无 AI/ML 背景的初学者。',
    lang: 'zh-CN',
    cleanUrls: true,
    lastUpdated: true,
    // 以仓库根为源目录，直接把现有 part-* 目录当作站点结构
    srcExclude: [
      '.superpowers/**',
      '.vitepress/**',
      'code/**',
      'docs/**',
      'node_modules/**',
      'CLAUDE.md',
    ],
    // README.md 既做仓库首页，也做各 part 的目录页
    rewrites: (file) => {
      if (file === 'README.md') return 'index.md'
      if (/^part-\d[^/]*\/README\.md$/.test(file))
        return file.replace(/README\.md$/, 'index.md')
      return file
    },
    // code/ 目录不在源内，指向它的链接无法在站点中解析，构建时跳过死链检查
    ignoreDeadLinks: [/^\/code\//, /code\/part-\d/],

    // fastdom 是 CJS/UMD 包，直接以 ESM 引入时缺少 default 导出，需预打包
    vite: {
      optimizeDeps: {
        include: ['fastdom'],
      },
    },

    markdown: {
      theme: { light: 'github-light', dark: 'github-dark' },
      toc: { level: [2, 3] },
    },

    themeConfig: {
      siteTitle: 'Agent 原理及实践',
      nav: [{ text: '目录', link: '/' }],
      sidebar,
      outline: { level: [2, 3], label: '本页目录' },
      docFooter: { prev: '上一篇', next: '下一篇' },
      returnToTopLabel: '回到顶部',
      sidebarMenuLabel: '目录',
      darkModeSwitchLabel: '外观',
      lastUpdated: { text: '最后更新', formatOptions: { dateStyle: 'medium' } },
      search: {
        provider: 'local',
        options: {
          translations: {
            button: { buttonText: '搜索文档', buttonAriaLabel: '搜索文档' },
            modal: {
              displayDetails: '展开详情',
              resetButtonTitle: '清除',
              backButtonTitle: '返回',
              noResultsText: '没有找到结果',
              footer: { selectText: '选择', navigateText: '切换', closeText: '关闭' },
            },
          },
          miniSearch: {
            options: { tokenize },
            searchOptions: {
              fuzzy: 0.2,
              prefix: true,
              boost: { title: 4, text: 2, titles: 1 },
            },
          },
        },
      },
    },

    mermaid: {
      theme: 'base',
      fontFamily:
        '"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", ui-sans-serif, sans-serif',
      themeVariables: {
        primaryColor: '#eef1f6',
        primaryTextColor: '#101f38',
        primaryBorderColor: '#9aa8bd',
        lineColor: '#7d8ba1',
        secondaryColor: '#faf7ef',
        tertiaryColor: '#f6f7f9',
        fontSize: '14px',
      },
    },
  })
)
