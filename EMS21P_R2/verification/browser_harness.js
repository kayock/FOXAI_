const fs=require('fs');
const source=fs.readFileSync(process.argv[2],'utf8');
function need(name,ok){if(!ok){console.error(name);process.exit(1)}}
need('quick help button',source.includes("openExtensionHelp('quick')"));
need('manual button',source.includes("openExtensionHelp('manual')"));
need('modal hidden',source.includes('id=extHelpModal')&&source.includes('exthelpmodal hidden'));
need('advanced collapsed',source.includes('<details class="card wide extadvanced">'));
need('legend',source.includes('SAFE • read-only')&&source.includes('PREVIEW • no write')&&source.includes('APPROVAL • writes state'));
need('protected button',source.includes('protectedcontrol disabled')&&source.includes('>Protected</button>'));
need('preview wording',source.includes("'Preview Disable':'Preview Enable'"));
need('state existence',source.includes('state_file_exists')&&source.includes('NOT CREATED — reserved path'));
need('manifest labels',source.includes('Manifest records:')&&source.includes('Manifest Records'));
need('manual content',source.includes('What Disable Does')&&source.includes('Overrides and Restore Default')&&source.includes('Evidence and Recovery'));
need('no new install language',!source.includes('Extension Manager Phase 2.1 installer'));
console.log(JSON.stringify({passed:true,help_modal:true,advanced_collapsed:true,protected_control:true,state_file_clarity:true,manual:true,cheat_sheet:true}));
