import { defineConfig } from 'vite';
import { resolve } from 'path';
import { readFileSync, readdirSync, statSync, writeFileSync, mkdirSync } from 'fs';
import yaml from 'js-yaml';

/**
 * Vite plugin for building Grafana dashboards from source panels
 */
function dashboardBuilder() {
  const SOURCE_DIR = 'etc/grafana/dashboards-src';
  const DEST_DIR = 'etc/grafana/provisioning/dashboards';

  /**
   * Load a JSON or YAML file safely
   */
  function loadFile(path) {
    try {
      const content = readFileSync(path, 'utf-8');
      if (path.endsWith('.json')) {
        return JSON.parse(content);
      } else if (path.endsWith('.yml') || path.endsWith('.yaml')) {
        return yaml.load(content);
      }
      throw new Error(`Unsupported file type: ${path}`);
    } catch (err) {
      console.error(`❌ Error loading ${path}:`, err.message);
      return null;
    }
  }

  /**
   * Build a single dashboard from its source directory
   */
  function buildDashboard(dashboardDir) {
    const dashboardName = dashboardDir.split('/').pop();

    // Try loading YAML first, then fall back to JSON
    let dashboardMetaPath = `${dashboardDir}/_dashboard.yml`;
    let dashboard = loadFile(dashboardMetaPath);

    if (!dashboard) {
      dashboardMetaPath = `${dashboardDir}/_dashboard.yaml`;
      dashboard = loadFile(dashboardMetaPath);
    }

    if (!dashboard) {
      dashboardMetaPath = `${dashboardDir}/_dashboard.json`;
      dashboard = loadFile(dashboardMetaPath);
    }

    if (!dashboard) {
      console.error(`❌ Failed to load dashboard metadata: ${dashboardDir}/_dashboard.{yml,yaml,json}`);
      return;
    }

    // Load all panel files (excluding _dashboard.* and _common.*)
    const panels = [];
    const files = readdirSync(dashboardDir)
      .filter(f => (f.endsWith('.json') || f.endsWith('.yml') || f.endsWith('.yaml')) && !f.startsWith('_'))
      .sort();

    for (const file of files) {
      const panel = loadFile(`${dashboardDir}/${file}`);
      if (panel) {
        panels.push(panel);
      }
    }

    // Assign panel IDs based on filename (e.g., 101-panel-name.json -> id: 101)
    panels.forEach((panel, idx) => {
      const filename = files[idx];
      const match = filename.match(/^(\d+)-/);
      if (match) {
        panel.id = parseInt(match[1], 10);
      } else {
        panel.id = idx + 1;
      }
    });

    // Combine into final dashboard
    dashboard.panels = panels;

    // 1. Write consolidated dashboard to built/ (flat, for Grafana to provision)
    // Make UID unique by appending '-built' suffix
    const outDir = `${DEST_DIR}/built`;
    mkdirSync(outDir, { recursive: true });
    const consolidatedDashboard = {
      ...dashboard,
      uid: `${dashboard.uid}-built`,
      title: `${dashboard.title} (Built)`
    };
    const consolidatedPath = `${outDir}/${dashboardName}.json`;
    writeFileSync(consolidatedPath, JSON.stringify(consolidatedDashboard, null, 2));

    // 2. Write individual panel dashboards to src/<dashboard>/ (for testing panels in isolation)
    const srcDir = `${DEST_DIR}/src/${dashboardName}`;
    mkdirSync(srcDir, { recursive: true });

    // Write consolidated dashboard to src folder too (with -src suffix for unique UID)
    const srcConsolidatedDashboard = {
      ...dashboard,
      uid: `${dashboard.uid}-src`,
      title: `${dashboard.title} (Source)`
    };
    writeFileSync(`${srcDir}/${dashboardName}.json`, JSON.stringify(srcConsolidatedDashboard, null, 2));

    // Write each panel as its own standalone dashboard (for testing individual panels)
    panels.forEach((panel, idx) => {
      const filename = files[idx];
      const panelDashboard = {
        ...dashboard,
        title: `${dashboard.title} - ${panel.title || filename}`,
        uid: `${dashboard.uid}-panel-${panel.id}`,
        panels: [panel] // Single panel dashboard
      };
      writeFileSync(`${srcDir}/${filename}`, JSON.stringify(panelDashboard, null, 2));
    });

    const timestamp = new Date().toLocaleTimeString();
    console.log(`[${timestamp}] ✅ Built ${panels.length} panels → built/${dashboardName}.json + src/${dashboardName}/ (${panels.length + 1} dashboards)`);

    return consolidatedPath;
  }

  /**
   * Build all dashboards
   */
  function buildAllDashboards() {
    const dashboards = readdirSync(SOURCE_DIR).filter(name => {
      const stat = statSync(`${SOURCE_DIR}/${name}`);
      return stat.isDirectory();
    });

    console.log(`\n🔨 Building ${dashboards.length} dashboards...\n`);

    for (const dashboard of dashboards) {
      buildDashboard(`${SOURCE_DIR}/${dashboard}`);
    }

    console.log(`\n✅ All dashboards built successfully\n`);
  }

  return {
    name: 'dashboard-builder',

    // Build all dashboards on startup
    buildStart() {
      buildAllDashboards();
    },

    // Watch for changes to source files
    configureServer(server) {
      const chokidar = server.watcher;

      // Watch both JSON and YAML files
      chokidar.add(`${SOURCE_DIR}/**/*.json`);
      chokidar.add(`${SOURCE_DIR}/**/*.yml`);
      chokidar.add(`${SOURCE_DIR}/**/*.yaml`);

      chokidar.on('change', (path) => {
        if (path.includes(SOURCE_DIR)) {
          const timestamp = new Date().toLocaleTimeString();
          const relativePath = path.replace(process.cwd() + '/', '');
          console.log(`\n[${timestamp}] 📝 Changed: ${relativePath}`);

          // Find which dashboard this file belongs to
          const dashboardMatch = path.match(new RegExp(`${SOURCE_DIR}/([^/]+)/`));
          if (dashboardMatch) {
            const dashboardName = dashboardMatch[1];
            buildDashboard(`${SOURCE_DIR}/${dashboardName}`);
          }
        }
      });

      chokidar.on('add', (path) => {
        if (path.includes(SOURCE_DIR) && (path.endsWith('.json') || path.endsWith('.yml') || path.endsWith('.yaml'))) {
          const timestamp = new Date().toLocaleTimeString();
          const relativePath = path.replace(process.cwd() + '/', '');
          console.log(`\n[${timestamp}] ➕ Added: ${relativePath}`);

          const dashboardMatch = path.match(new RegExp(`${SOURCE_DIR}/([^/]+)/`));
          if (dashboardMatch) {
            const dashboardName = dashboardMatch[1];
            buildDashboard(`${SOURCE_DIR}/${dashboardName}`);
          }
        }
      });
    }
  };
}

export default defineConfig({
  plugins: [dashboardBuilder()],
  // Minimal server config (we don't actually serve anything)
  server: {
    port: 5174,
    open: false
  },
  // Disable building since we're only using the dev server for watching
  build: {
    watch: {}
  }
});
