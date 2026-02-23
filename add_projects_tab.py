#!/usr/bin/env python3
"""Add On-Going Projects tab to TNT Dashboard"""

import re
from pathlib import Path

DASHBOARD_PATH = Path(__file__).parent / 'index.html'

def main():
    print("\U0001F4CB Adding On-Going Projects tab...")
    html = DASHBOARD_PATH.read_text(encoding='utf-8')
    
    # Remove old projects content if exists
    html = re.sub(r'<!-- Projects Tab Content -->.*?<!-- End Projects Tab Content -->', '', html, flags=re.DOTALL)
    
    # Add tab button if not present
    if 'tab-projects' not in html:
        btn = '''\n                <button onclick="switchTab('projects')" id="tab-projects"
                        class="tab-btn border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 py-4 px-1 text-sm font-medium">
                    \U0001F4C1 On-Going Projects
                </button>'''
        # Insert before closing </nav>
        html = html.replace('</nav>', btn + '\n            </nav>', 1)
    
    # Update switchTab to include projects-content
    # Find the array of content IDs and add projects-content if missing
    if "'projects-content'" not in html:
        html = html.replace(
            "['tnt-content', 'wtw-content', 'leak-content', 'terminal-content']",
            "['tnt-content', 'wtw-content', 'leak-content', 'terminal-content', 'projects-content']"
        )
        # Also handle case where terminal hasn't been added yet
        html = html.replace(
            "['tnt-content', 'wtw-content', 'leak-content']",
            "['tnt-content', 'wtw-content', 'leak-content', 'projects-content']"
        )
    
    # Create the projects tab content
    projects_html = '''
    <!-- Projects Tab Content -->
    <div id="projects-content" class="hidden">
        <main class="max-w-7xl mx-auto px-4 py-6">
            <!-- Header -->
            <div class="bg-gradient-to-r from-indigo-600 to-purple-500 rounded-lg shadow-lg p-6 mb-8 text-white">
                <div class="flex justify-between items-center">
                    <div>
                        <h2 class="text-2xl font-bold">\U0001F4C1 On-Going Projects</h2>
                        <p class="text-indigo-100 mt-1">Project tracking and status updates</p>
                    </div>
                </div>
            </div>
            
            <!-- Coming Soon Card -->
            <div class="max-w-2xl mx-auto mt-12">
                <div class="bg-white rounded-2xl shadow-xl overflow-hidden">
                    <div class="bg-gradient-to-r from-purple-50 to-indigo-50 p-8 text-center">
                        <div class="inline-flex items-center justify-center w-20 h-20 bg-indigo-100 rounded-full mb-6">
                            <svg class="w-10 h-10 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"></path>
                            </svg>
                        </div>
                        <div class="inline-block px-4 py-1 bg-indigo-600 text-white text-xs font-bold uppercase tracking-wider rounded-full mb-4">
                            Coming Soon
                        </div>
                        <h3 class="text-2xl font-bold text-gray-900 mb-3">Wrike Integration</h3>
                        <p class="text-gray-600 text-lg leading-relaxed max-w-md mx-auto">
                            We\'re building a live connection to <span class="font-semibold text-indigo-600">Wrike</span> to pull project data directly into this dashboard.
                        </p>
                    </div>
                    <div class="p-6 bg-white">
                        <div class="space-y-4">
                            <div class="flex items-start gap-3">
                                <span class="flex-shrink-0 w-6 h-6 bg-green-100 text-green-600 rounded-full flex items-center justify-center text-sm font-bold">\u2713</span>
                                <div>
                                    <p class="font-semibold text-gray-800">Real-time project status</p>
                                    <p class="text-sm text-gray-500">See active projects, timelines, and milestones without switching tools</p>
                                </div>
                            </div>
                            <div class="flex items-start gap-3">
                                <span class="flex-shrink-0 w-6 h-6 bg-green-100 text-green-600 rounded-full flex items-center justify-center text-sm font-bold">\u2713</span>
                                <div>
                                    <p class="font-semibold text-gray-800">Filter by region & director</p>
                                    <p class="text-sm text-gray-500">Same cascading filters you already use on every other tab</p>
                                </div>
                            </div>
                            <div class="flex items-start gap-3">
                                <span class="flex-shrink-0 w-6 h-6 bg-green-100 text-green-600 rounded-full flex items-center justify-center text-sm font-bold">\u2713</span>
                                <div>
                                    <p class="font-semibold text-gray-800">One place for everything</p>
                                    <p class="text-sm text-gray-500">HVAC performance + project tracking in a single dashboard</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="px-6 py-4 bg-gray-50 border-t border-gray-100 text-center">
                        <p class="text-sm text-gray-400">Questions? Reach out &mdash; James Savage &bull; 918-308-0662</p>
                    </div>
                </div>
            </div>
        </main>
    </div>
    <!-- End Projects Tab Content -->
    '''
    
    # Insert before </body>
    html = html.replace('</body>', projects_html + '\n</body>')
    
    DASHBOARD_PATH.write_text(html, encoding='utf-8')
    print("   \u2705 On-Going Projects tab added!")

if __name__ == '__main__':
    main()
