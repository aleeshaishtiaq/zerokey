/* Local-only demo data. Every record below is fictional. */
const customers = [
  {id:'TCL-CU-2041',name:'Sara Malik',service:'Fiber',contact:'+92 300 555 0101',email:'sara.malik@gmail.com',address:'Demo Sector 01, Islamabad',started:'Mar 14, 2024',router:'DEMO-RTR-2041',status:'Active',package:'Fiber Home 100',bill:4499,dues:0,signal:-48,complaint:'None',account:'DEMO-AC-70041',dueDate:'Oct 24, 2026',payment:'Paid',lastPayment:'Oct 03, 2026',history:['Oct 03 · Monthly bill marked paid','Sep 18 · Signal check completed','Sep 03 · Monthly bill marked paid']},
  {id:'TCL-CU-2042',name:'Hamza Qureshi',service:'Broadband',contact:'+92 300 555 0102',email:'hamza.qureshi@yahoo.com',address:'Demo Sector 02, Islamabad',started:'Jun 08, 2023',router:'DEMO-RTR-2042',status:'Active',package:'Home Plus 50',bill:3299,dues:3299,signal:-62,complaint:'Open',account:'DEMO-AC-70042',dueDate:'Oct 18, 2026',payment:'Overdue',lastPayment:'Sep 02, 2026',history:['Oct 08 · Intermittent connection complaint opened','Sep 02 · Monthly bill marked paid']},
  {id:'TCL-CU-2043',name:'Noor Ahmed',service:'Bundle',contact:'+92 300 555 0103',email:'noor.ahmed@gmail.com',address:'Demo Block 03, Rawalpindi',started:'Jan 22, 2025',router:'DEMO-RTR-2043',status:'Active',package:'Family Connect',bill:5799,dues:0,signal:-51,complaint:'None',account:'DEMO-AC-70043',dueDate:'Oct 28, 2026',payment:'Paid',lastPayment:'Oct 06, 2026',history:['Oct 06 · Monthly bill marked paid','Sep 21 · Package review completed']},
  {id:'TCL-CU-2044',name:'Zainab Raza',service:'Fiber',contact:'+92 300 555 0104',email:'zainab.raza@yahoo.com',address:'Demo Avenue 04, Lahore',started:'Oct 10, 2026',router:'DEMO-RTR-2044',status:'Pending',package:'Fiber Home 50',bill:2799,dues:2799,signal:-72,complaint:'Installation',account:'DEMO-AC-70044',dueDate:'Oct 30, 2026',payment:'Due',lastPayment:'Not recorded',history:['Oct 11 · New connection installation scheduled','Oct 10 · Request created']},
  {id:'TCL-CU-2045',name:'Omar Siddiqui',service:'Landline',contact:'+92 300 555 0105',email:'omar.siddiqui@gmail.com',address:'Demo Street 05, Karachi',started:'Aug 19, 2022',router:'DEMO-RTR-2045',status:'Active',package:'Talk & Connect',bill:1899,dues:950,signal:-58,complaint:'In progress',account:'DEMO-AC-70045',dueDate:'Oct 20, 2026',payment:'Due',lastPayment:'Sep 20, 2026',history:['Oct 09 · Landline fault assigned to Voice Support','Sep 20 · Partial bill payment recorded']},
  {id:'TCL-CU-2046',name:'Mariam Iqbal',service:'Broadband',contact:'+92 300 555 0106',email:'mariam.iqbal@yahoo.com',address:'Demo Sector 06, Islamabad',started:'Feb 02, 2024',router:'DEMO-RTR-2046',status:'Active',package:'Home Plus 75',bill:3899,dues:0,signal:-55,complaint:'Resolved',account:'DEMO-AC-70046',dueDate:'Oct 25, 2026',payment:'Paid',lastPayment:'Oct 02, 2026',history:['Oct 07 · Speed concern resolved','Oct 02 · Monthly bill marked paid']},
  {id:'TCL-CU-2047',name:'Bilal Hussain',service:'Fiber',contact:'+92 300 555 0107',email:'bilal.hussain@gmail.com',address:'Demo Block 07, Faisalabad',started:'Nov 27, 2023',router:'DEMO-RTR-2047',status:'Suspended',package:'Fiber Home 25',bill:2199,dues:6597,signal:-83,complaint:'Open',account:'DEMO-AC-70047',dueDate:'Oct 12, 2026',payment:'Overdue',lastPayment:'Jul 04, 2026',history:['Oct 10 · Service temporarily suspended','Oct 09 · Payment reminder logged']},
  {id:'TCL-CU-2048',name:'Areeba Khan',service:'Bundle',contact:'+92 300 555 0108',email:'areeba.khan@yahoo.com',address:'Demo Avenue 08, Lahore',started:'May 05, 2025',router:'DEMO-RTR-2048',status:'Active',package:'Complete Connect',bill:6499,dues:0,signal:-46,complaint:'None',account:'DEMO-AC-70048',dueDate:'Oct 26, 2026',payment:'Paid',lastPayment:'Oct 05, 2026',history:['Oct 05 · Monthly bill marked paid','Sep 14 · Package upgrade completed']},
  {id:'TCL-CU-2049',name:'Daniyal Farooq',service:'Broadband',contact:'+92 300 555 0109',email:'daniyal.farooq@gmail.com',address:'Demo Street 09, Peshawar',started:'Sep 16, 2024',router:'DEMO-RTR-2049',status:'Active',package:'Home Plus 50',bill:3299,dues:3299,signal:-67,complaint:'Open',account:'DEMO-AC-70049',dueDate:'Oct 16, 2026',payment:'Due',lastPayment:'Sep 16, 2026',history:['Oct 12 · Wi-Fi signal review requested','Sep 16 · Monthly bill marked paid']}
];

let tickets = [
  {id:'TCL-2407',customerId:'TCL-CU-2042',category:'Internet connectivity',priority:'High',created:'Oct 08, 2026',team:'Network Support',status:'Open',description:'Intermittent connection reported during evening use.',updates:['Oct 08 · Ticket created by demo operations','Oct 09 · Assigned to Network Support']},
  {id:'TCL-2408',customerId:'TCL-CU-2045',category:'Landline fault',priority:'Medium',created:'Oct 09, 2026',team:'Voice Support',status:'In Progress',description:'Outgoing calls have intermittent audio.',updates:['Oct 09 · Ticket created by demo operations','Oct 10 · Voice Support investigating']},
  {id:'TCL-2411',customerId:'TCL-CU-2044',category:'Installation',priority:'Medium',created:'Oct 10, 2026',team:'Field Services',status:'Open',description:'Confirm installation appointment and access details.',updates:['Oct 10 · Installation request logged','Oct 11 · Field Services assigned']},
  {id:'TCL-2413',customerId:'TCL-CU-2049',category:'Package upgrade',priority:'Normal',created:'Oct 12, 2026',team:'Customer Care',status:'Open',description:'Customer is interested in a faster home package.',updates:['Oct 12 · Upgrade request logged']},
  {id:'TCL-2414',customerId:'TCL-CU-2046',category:'Internet connectivity',priority:'Low',created:'Oct 07, 2026',team:'Network Support',status:'Resolved',description:'Speed concern reviewed and closed in demo data.',updates:['Oct 07 · Speed check completed','Oct 08 · Marked resolved']},
  {id:'TCL-2415',customerId:'TCL-CU-2043',category:'New connection',priority:'Normal',created:'Oct 11, 2026',team:'Provisioning',status:'In Progress',description:'Provisioning a requested secondary connection.',updates:['Oct 11 · Request received','Oct 12 · Provisioning in progress']},
  {id:'TCL-2416',customerId:'TCL-CU-2047',category:'Disconnection',priority:'Medium',created:'Oct 11, 2026',team:'Account Services',status:'Open',description:'Review requested service disconnection date.',updates:['Oct 11 · Request received']}
];

const profile = {name:'Amina Shah',employeeId:'TCL-EMP-1048',department:'Customer Operations',designation:'Operations Manager',email:'amina.shah@tclgroup.com',phone:'+92 300 555 0148'};
const suggestions = ['Move the router to a central location','Reduce physical obstructions around the access point','Select a less congested Wi-Fi channel','Move closer to the access point for stronger signal','Review connected devices and disconnect unused devices'];
const $ = (selector, root=document) => root.querySelector(selector);
const $$ = (selector, root=document) => [...root.querySelectorAll(selector)];
const money = amount => `PKR ${Number(amount).toLocaleString('en-PK')}`;
const remainingDues = customer => customer.payment==='Paid'?0:Number(customer.dues)||Number(customer.bill);
const initials = name => name.split(/\s+/).slice(0,2).map(part=>part[0]).join('').toUpperCase();
const escapeHtml = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const openTicketCount = () => tickets.filter(ticket=>ticket.status==='Open').length;
let customerSort = {key:'name',direction:1};
let toastTimer;

function showToast(message,type='success') {
  const region=$('#toast-region');
  const toast=document.createElement('div');
  toast.className=`toast ${type}`;
  toast.innerHTML=`<span class="toast-icon">${type==='error'?'!':type==='warning'?'i':'✓'}</span><span>${escapeHtml(message)}</span>`;
  region.append(toast);
  window.setTimeout(()=>toast.remove(),3600);
}

function switchSection(name) {
  const target=$(`#section-${name}`);
  if(!target) return;
  $$('.view-section').forEach(section=>section.classList.toggle('active',section===target));
  $$('.nav-link[data-section]').forEach(link=>link.classList.toggle('active',link.dataset.section===name));
  $('#current-page-title').textContent=target.dataset.title;
  $('#profile-menu').classList.add('is-hidden');
  $('#sidebar').classList.remove('mobile-open');
  $('#sidebar-backdrop').classList.remove('visible');
  window.scrollTo({top:0,behavior:'smooth'});
  if(name==='customers') renderCustomers();
  if(name==='tickets') renderTickets();
  if(name==='billing') renderBilling();
}

function renderOverview() {
  $('#welcome-name').textContent=profile.name.split(' ')[0];
  $('#topbar-employee-name').textContent=profile.name;
  $('#profile-name').textContent=profile.name;
  $('#profile-designation').textContent=profile.designation;
  $('#profile-designation-detail').textContent=profile.designation;
  $('#profile-department').textContent=profile.department;
  $('#profile-email').textContent=profile.email;
  $('#profile-phone').textContent=profile.phone;
  $$('.avatar').forEach(avatar=>avatar.textContent=initials(profile.name));
  $('#customer-nav-count').textContent=String(customers.length).padStart(2,'0');
  $('#metric-open-tickets').textContent=openTicketCount();
  $('#ticket-nav-count').textContent=String(openTicketCount()).padStart(2,'0');
  $('#overview-customer-rows').innerHTML=customers.slice(0,4).map(customer=>`<tr><td><div class="customer-cell"><span class="customer-avatar">${initials(customer.name)}</span><span><span class="customer-name">${escapeHtml(customer.name)}</span><span class="customer-id">${customer.id}</span></span></div></td><td><span class="service-pill"><i></i>${customer.service}</span></td><td>${statusBadge(customer.status)}</td><td>${money(customer.bill)}</td><td><span class="signal-cell"><span class="signal-mini ${signalClass(customer.signal)}"><i></i><i></i><i></i><i></i></span>${customer.signal} dBm</span></td></tr>`).join('');
}

function statusBadge(status) {
  const classes={'Active':'status-active','Suspended':'status-suspended','Pending':'status-pending','Open':'status-open','In Progress':'status-progress','Resolved':'status-resolved','Paid':'status-paid','Due':'status-due','Overdue':'status-overdue'};
  return `<span class="status-pill ${classes[status]||'status-open'}">${escapeHtml(status)}</span>`;
}
function signalClass(signal){return signal>-55?'':signal>-70?'medium':'low';}

function filteredCustomers() {
  const query=$('#customer-search').value.trim().toLowerCase();
  const status=$('#customer-status-filter').value;
  const service=$('#customer-service-filter').value;
  return customers.filter(customer=>(!query||`${customer.name} ${customer.id}`.toLowerCase().includes(query))&&(!status||customer.status===status)&&(!service||customer.service===service)).sort((a,b)=>{
    const first=a[customerSort.key],second=b[customerSort.key];
    return (typeof first==='number'?first-second:String(first).localeCompare(String(second)))*customerSort.direction;
  });
}

function renderCustomers() {
  const rows=filteredCustomers();
  $('#customer-rows').innerHTML=rows.map(customer=>`<tr>
    <td><button class="customer-open-link" data-customer-view="${customer.id}">${customer.id}</button></td><td><div class="customer-cell"><span class="customer-avatar">${initials(customer.name)}</span><button class="customer-open-link" data-customer-view="${customer.id}">${escapeHtml(customer.name)}</button></div></td>
    <td><span class="service-pill"><i></i>${escapeHtml(customer.service)}</span></td><td>${escapeHtml(customer.contact)}</td><td>${statusBadge(customer.status)}</td><td>${escapeHtml(customer.package)}</td><td>${money(customer.bill)}</td><td>${remainingDues(customer)?money(remainingDues(customer)):'<span class="muted">—</span>'}</td>
    <td><span class="signal-cell"><span class="signal-mini ${signalClass(customer.signal)}"><i></i><i></i><i></i><i></i></span>${customer.signal} dBm</span></td><td>${customer.complaint==='None'?'<span class="muted">None</span>':statusBadge(customer.complaint==='In progress'?'In Progress':customer.complaint)}</td>
    <td><div class="row-actions"><button class="row-action" data-customer-view="${customer.id}" title="View details" aria-label="View ${escapeHtml(customer.name)} details">⌕</button><button class="row-action" data-customer-edit="${customer.id}" title="Edit customer" aria-label="Edit ${escapeHtml(customer.name)}">✎</button><button class="row-action delete" data-customer-delete="${customer.id}" title="Delete customer" aria-label="Delete ${escapeHtml(customer.name)}">×</button></div></td></tr>`).join('');
  $('#customer-empty').classList.toggle('is-hidden',rows.length>0);
  $('#customer-record-count').textContent=`${rows.length} records`;
  $('#customer-table-summary').textContent=`Showing ${rows.length} of ${customers.length} customer records`;
}

function csvEscape(value){return `"${String(value).replace(/"/g,'""')}"`;}
function exportCustomers() {
  const rows=filteredCustomers();
  if(!rows.length){showToast('There are no filtered customer records to export.','warning');return;}
  if(!window.confirm(`Export ${rows.length} currently filtered customer record(s) as CSV?`)) return;
  const columns=[['Customer ID','id'],['Customer Name','name'],['Service Type','service'],['Registered Contact','contact'],['Connection Status','status'],['Package','package'],['Monthly Bill (PKR)','bill'],['Remaining Dues (PKR)','dues'],['Signal Strength (dBm)','signal'],['Complaint Status','complaint']];
  const csv=[columns.map(item=>csvEscape(item[0])).join(','),...rows.map(row=>columns.map(([,key])=>csvEscape(key==='dues'?remainingDues(row):row[key])).join(','))].join('\r\n');
  const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));link.download='tcl-customers.csv';document.body.append(link);link.click();link.remove();URL.revokeObjectURL(link.href);
  showToast(`${rows.length} customer records exported.`);
}

function dialogFrame(title,subtitle,body,actions='') {
  $('#app-dialog').classList.remove('customer-detail-dialog');
  $('#dialog-content').innerHTML=`<div class="dialog-heading"><div><h2 id="dialog-title">${escapeHtml(title)}</h2><p>${escapeHtml(subtitle)}</p></div><button class="dialog-close" type="button" data-dialog-close aria-label="Close dialog">×</button></div>${body}${actions?`<div class="dialog-actions">${actions}</div>`:''}`;
  $('#app-dialog').showModal();
}
function closeDialog(){if($('#app-dialog').open)$('#app-dialog').close();}

function showCustomerDetails(id) {
  const customer=customers.find(item=>item.id===id);if(!customer)return;
  const customerTickets=tickets.filter(ticket=>ticket.customerId===customer.id);
  const ticketHistory=customerTickets.length?customerTickets.map(ticket=>`<div class="customer-ticket"><span class="ticket-ref">${ticket.id}</span><span class="customer-ticket-copy"><strong>${escapeHtml(ticket.category)}</strong><small>${escapeHtml(ticket.description)}</small></span><span class="customer-ticket-meta">${ticket.priority}<br>${statusBadge(ticket.status)}</span></div>`).join(''):'<p class="customer-empty-note">No service tickets are linked to this customer.</p>';
  const body=`<div class="customer-profile-banner"><span class="customer-avatar customer-avatar-large">${initials(customer.name)}</span><div class="customer-profile-name"><h3>${escapeHtml(customer.name)}</h3><span>${customer.id} <i>·</i> ${escapeHtml(customer.service)} customer</span></div>${statusBadge(customer.status)}</div>
    <section class="customer-detail-section"><div class="customer-section-title"><span>01</span><h3>Customer information</h3></div><div class="detail-grid"><div class="detail-item"><span>EMAIL ADDRESS</span><strong>${escapeHtml(customer.email)}</strong></div><div class="detail-item"><span>REGISTERED PHONE</span><strong>${escapeHtml(customer.contact)}</strong></div><div class="detail-item"><span>SERVICE ADDRESS</span><strong>${escapeHtml(customer.address)}</strong></div><div class="detail-item"><span>ACCOUNT REFERENCE</span><strong>${customer.account}</strong></div><div class="detail-item"><span>CUSTOMER SINCE</span><strong>${customer.started}</strong></div><div class="detail-item"><span>CONNECTION STATUS</span><strong>${statusBadge(customer.status)}</strong></div></div></section>
    <section class="customer-detail-section"><div class="customer-section-title"><span>02</span><h3>Service &amp; network</h3></div><div class="detail-grid"><div class="detail-item"><span>SERVICE PACKAGE</span><strong>${escapeHtml(customer.package)}</strong></div><div class="detail-item"><span>SERVICE TYPE</span><strong>${escapeHtml(customer.service)}</strong></div><div class="detail-item"><span>ROUTER ID</span><strong>${customer.router}</strong></div><div class="detail-item"><span>WI-FI SIGNAL</span><strong>${customer.signal} dBm · ${customer.signal>-55?'Very good':customer.signal>-70?'Good':'Needs review'}</strong></div></div></section>
    <section class="customer-detail-section"><div class="customer-section-title"><span>03</span><h3>Billing summary</h3></div><div class="detail-grid"><div class="detail-item"><span>MONTHLY BILL</span><strong>${money(customer.bill)}</strong></div><div class="detail-item"><span>REMAINING DUES</span><strong>${money(remainingDues(customer))}</strong></div><div class="detail-item"><span>PAYMENT STATUS</span><strong>${statusBadge(customer.payment)}</strong></div><div class="detail-item"><span>DUE DATE</span><strong>${customer.dueDate}</strong></div><div class="detail-item"><span>LAST PAYMENT</span><strong>${customer.lastPayment}</strong></div></div></section>
    <section class="customer-detail-section"><div class="customer-section-title"><span>04</span><h3>Complaints &amp; service history</h3><span class="customer-ticket-count">${customerTickets.length} ticket${customerTickets.length===1?'':'s'}</span></div><div class="customer-ticket-list">${ticketHistory}</div><div class="history-list customer-history-list">${customer.history.map(line=>`<div class="history-item"><span>${escapeHtml(line)}</span></div>`).join('')}</div></section>
    `;
  dialogFrame('Customer profile',`${customer.id} · Customer account`,body,`<button class="button button-outline button-small" data-customer-edit="${customer.id}">Edit customer</button><button class="button button-primary button-small" data-dialog-close>Done</button>`);
  $('#app-dialog').classList.add('customer-detail-dialog');
}

function editCustomer(id) {
  const customer=customers.find(item=>item.id===id);if(!customer)return;
  const serviceOptions=['Fiber','Broadband','Landline','Bundle'].map(value=>`<option ${customer.service===value?'selected':''}>${value}</option>`).join('');
  const statusOptions=['Active','Suspended','Pending'].map(value=>`<option ${customer.status===value?'selected':''}>${value}</option>`).join('');
  const body=`<form class="dialog-form" id="customer-edit-form"><label>Customer name<input name="name" value="${escapeHtml(customer.name)}" required></label><label>Registered contact<input name="contact" value="${escapeHtml(customer.contact)}" required></label><label>Service type<select name="service">${serviceOptions}</select></label><label>Connection status<select name="status">${statusOptions}</select></label><label>Package<input name="package" value="${escapeHtml(customer.package)}" required></label><label>Monthly bill (PKR)<input name="bill" type="number" min="0" value="${customer.bill}" required></label><label>Remaining dues (PKR)<input name="dues" type="number" min="0" value="${remainingDues(customer)}" required></label><label>Signal strength (dBm)<input name="signal" type="number" min="-100" max="-20" value="${customer.signal}" required></label></form>`;
  dialogFrame('Edit customer',`${customer.id} · Customer account`,body,`<button class="button button-outline button-small" data-dialog-close>Cancel</button><button class="button button-primary button-small" type="submit" form="customer-edit-form">Save changes</button>`);
  $('#customer-edit-form').addEventListener('submit',event=>{event.preventDefault();const data=new FormData(event.currentTarget);Object.assign(customer,{name:data.get('name').trim(),contact:data.get('contact').trim(),service:data.get('service'),status:data.get('status'),package:data.get('package').trim(),bill:Number(data.get('bill')),dues:Number(data.get('dues')),signal:Number(data.get('signal'))});closeDialog();renderCustomers();renderOverview();showToast(`${customer.id} demo record updated.`);});
}

function deleteCustomer(id) {
  const customer=customers.find(item=>item.id===id);if(!customer)return;
  if(!window.confirm(`Delete customer ${customer.name} (${customer.id})?`))return;
  customers.splice(customers.indexOf(customer),1);renderCustomers();renderOverview();renderBilling();showToast(`${customer.id} removed.`);
}

function filteredTickets() {
  const query=$('#ticket-search').value.trim().toLowerCase(),status=$('#ticket-status-filter').value,category=$('#ticket-category-filter').value;
  return tickets.filter(ticket=>(!query||`${ticket.id} ${ticket.customerId} ${ticket.category} ${ticket.team}`.toLowerCase().includes(query))&&(!status||ticket.status===status)&&(!category||ticket.category===category));
}
function renderTickets() {
  const rows=filteredTickets();
  $('#ticket-rows').innerHTML=rows.map(ticket=>`<tr><td><strong class="customer-name">${ticket.id}</strong></td><td>${ticket.customerId}</td><td>${escapeHtml(ticket.category)}</td><td><span class="priority-pill priority-${ticket.priority.toLowerCase()}">${ticket.priority}</span></td><td>${ticket.created}</td><td>${escapeHtml(ticket.team)}</td><td>${statusBadge(ticket.status)}</td><td><button class="row-action" data-ticket-view="${ticket.id}" title="View ticket" aria-label="View ${ticket.id}">⌕</button></td></tr>`).join('');
  $('#ticket-empty').classList.toggle('is-hidden',rows.length>0);
  $('#ticket-record-count').textContent=`${rows.length} tickets`;
  $('#ticket-table-summary').textContent=`Showing ${rows.length} of ${tickets.length} simulated tickets`;
  $('#ticket-open-count').textContent=openTicketCount();
  $('#ticket-progress-count').textContent=tickets.filter(ticket=>ticket.status==='In Progress').length;
  $('#ticket-resolved-count').textContent=tickets.filter(ticket=>ticket.status==='Resolved').length;
  $('#ticket-total-count').textContent=tickets.length;
  $('#metric-open-tickets').textContent=openTicketCount();
  $('#ticket-nav-count').textContent=String(openTicketCount()).padStart(2,'0');
}

function ticketDetails(id) {
  const ticket=tickets.find(item=>item.id===id);if(!ticket)return;
  const customer=customers.find(item=>item.id===ticket.customerId);
  const history=ticket.updates.map(update=>`<div class="history-item"><span>${escapeHtml(update)}</span></div>`).join('');
  const body=`<div class="detail-grid"><div class="detail-item"><span>TICKET ID</span><strong>${ticket.id}</strong></div><div class="detail-item"><span>STATUS</span><strong>${ticket.status}</strong></div><div class="detail-item"><span>CUSTOMER</span><strong>${ticket.customerId}${customer?` · ${escapeHtml(customer.name)}`:''}</strong></div><div class="detail-item"><span>CATEGORY / PRIORITY</span><strong>${escapeHtml(ticket.category)} · ${ticket.priority}</strong></div><div class="detail-item"><span>CREATED</span><strong>${ticket.created}</strong></div><div class="detail-item"><span>ASSIGNED TEAM</span><strong>${escapeHtml(ticket.team)}</strong></div></div><p class="dialog-section-label">ISSUE DESCRIPTION</p><p class="dialog-note">${escapeHtml(ticket.description)}</p><p class="dialog-section-label">ACTIVITY HISTORY</p><div class="history-list">${history}</div><div class="dialog-status-action"><span>Update demo ticket status</span><select id="ticket-detail-status"><option ${ticket.status==='Open'?'selected':''}>Open</option><option ${ticket.status==='In Progress'?'selected':''}>In Progress</option><option ${ticket.status==='Resolved'?'selected':''}>Resolved</option></select></div>`;
  dialogFrame('Ticket details',`${ticket.id} · Simulated service desk`,body,`<button class="button button-outline button-small" data-dialog-close>Close</button><button class="button button-primary button-small" id="save-ticket-status" data-ticket-status="${ticket.id}">Save status</button>`);
}

function createTicketDialog() {
  const customerOptions=customers.map(customer=>`<option value="${customer.id}">${customer.id} · ${escapeHtml(customer.name)}</option>`).join('');
  const categories=['Internet connectivity','Landline fault','New connection','Package upgrade','Installation','Disconnection'].map(item=>`<option>${item}</option>`).join('');
  const body=`<form class="dialog-form" id="ticket-create-form"><label class="field-full">Customer<select name="customerId" required>${customerOptions}</select></label><label>Issue category<select name="category">${categories}</select></label><label>Priority<select name="priority"><option>Normal</option><option>Low</option><option>Medium</option><option>High</option></select></label><label class="field-full">Complaint description<textarea name="description" placeholder="Describe the service issue for this demo ticket" aria-describedby="ticket-telemetry-note" required></textarea><small class="ticket-telemetry-note" id="ticket-telemetry-note">Please use fictional details only. Typed text stays on this page; only keyboard and mouse timing summaries are sent to the local telemetry API.</small><span class="ticket-telemetry-status" id="telemetry-status" role="status" aria-live="polite">Waiting for the ZeroKey extension to load.</span></label></form>`;
  dialogFrame('Create a demo ticket','Add a fictional customer service request',body,`<button class="button button-outline button-small" data-dialog-close>Cancel</button><button class="button button-primary button-small" type="submit" form="ticket-create-form">Create ticket</button>`);
  $('#ticket-create-form').addEventListener('submit',event=>{event.preventDefault();const data=new FormData(event.currentTarget);const id=`TCL-${2420+tickets.length}`;const categories=data.get('category');const teams={'Internet connectivity':'Network Support','Landline fault':'Voice Support','New connection':'Provisioning','Package upgrade':'Customer Care','Installation':'Field Services','Disconnection':'Account Services'};tickets.unshift({id,customerId:data.get('customerId'),category:categories,priority:data.get('priority'),created:'Oct 13, 2026',team:teams[categories],status:'Open',description:data.get('description').trim(),updates:['Oct 13 · Ticket created in local demo']});closeDialog();renderTickets();showToast(`${id} created in the demo queue.`);});
}

function filteredBilling() {
  const query=$('#billing-search').value.trim().toLowerCase(),status=$('#billing-status-filter').value;
  return customers.filter(customer=>(!query||`${customer.id} ${customer.name} ${customer.account}`.toLowerCase().includes(query))&&(!status||customer.payment===status));
}
function renderBilling() {
  const rows=filteredBilling();
  $('#billing-rows').innerHTML=rows.map(customer=>`<tr><td><strong class="customer-name">${customer.id}</strong></td><td>${escapeHtml(customer.name)}</td><td>${money(customer.bill)}</td><td>${customer.dueDate}</td><td>${statusBadge(customer.payment)}</td><td>${customer.lastPayment}</td><td><button class="row-action" data-billing-view="${customer.id}" title="View billing details" aria-label="View billing for ${escapeHtml(customer.name)}">⌕</button></td></tr>`).join('');
  $('#billing-empty').classList.toggle('is-hidden',rows.length>0);
  $('#billing-record-count').textContent=`${rows.length} accounts`;
  $('#billing-table-summary').textContent=`Showing ${rows.length} of ${customers.length} simulated accounts`;
  const outstanding=customers.reduce((sum,customer)=>sum+remainingDues(customer),0),average=customers.length?Math.round(customers.reduce((sum,customer)=>sum+customer.bill,0)/customers.length):0;
  $('#portfolio-outstanding').textContent=money(outstanding);
  $('#billing-current-count').textContent=customers.length;
  $('#billing-due-count').textContent=customers.filter(customer=>customer.payment==='Due'||customer.payment==='Overdue').length;
  $('#billing-paid-count').textContent=customers.filter(customer=>customer.payment==='Paid').length;
  $('#billing-average').textContent=money(average);
}
function billingDetails(id) {
  const customer=customers.find(item=>item.id===id);if(!customer)return;
  const body=`<div class="detail-grid"><div class="detail-item"><span>CUSTOMER / ACCOUNT</span><strong>${escapeHtml(customer.name)} · ${customer.id}</strong></div><div class="detail-item"><span>ACCOUNT REFERENCE</span><strong>${customer.account}</strong></div><div class="detail-item"><span>CURRENT BILL</span><strong>${money(customer.bill)}</strong></div><div class="detail-item"><span>PAYMENT STATUS</span><strong>${customer.payment}</strong></div><div class="detail-item"><span>REMAINING DUES</span><strong>${money(remainingDues(customer))}</strong></div><div class="detail-item"><span>DUE DATE</span><strong>${customer.dueDate}</strong></div></div><p class="dialog-section-label">PREVIOUS BILLING RECORDS</p><div class="history-list">${customer.history.filter(item=>item.toLowerCase().includes('bill')||item.toLowerCase().includes('payment')).map(item=>`<div class="history-item"><span>${escapeHtml(item)}</span></div>`).join('')||'<div class="history-item"><span>No previous payment record.</span></div>'}</div>`;
  dialogFrame('Billing details',`${customer.id} · Billing account`,body,`<button class="button button-primary button-small" data-dialog-close>Done</button>`);
}

function editProfileDialog() {
  const body=`<form class="dialog-form" id="profile-edit-form"><label>Employee name<input name="name" value="${escapeHtml(profile.name)}" required></label><label>Designation<input name="designation" value="${escapeHtml(profile.designation)}" required></label><label>Department<input name="department" value="${escapeHtml(profile.department)}" required></label><label>Work email<input name="email" type="email" value="${escapeHtml(profile.email)}" required></label><label class="field-full">Contact number<input name="phone" value="${escapeHtml(profile.phone)}" required></label></form><p class="dialog-note">Employee ID and assigned role are fixed in this fictional demo profile.</p>`;
  dialogFrame('Edit demo profile','Changes are stored for this browser session only',body,`<button class="button button-outline button-small" data-dialog-close>Cancel</button><button class="button button-primary button-small" type="submit" form="profile-edit-form">Save profile</button>`);
  $('#profile-edit-form').addEventListener('submit',event=>{event.preventDefault();const data=new FormData(event.currentTarget);Object.assign(profile,{name:data.get('name').trim(),designation:data.get('designation').trim(),department:data.get('department').trim(),email:data.get('email').trim(),phone:data.get('phone').trim()});closeDialog();renderOverview();showToast('Demo profile updated for this session.');});
}

function renderSuggestions(items=suggestions) {
  $('#suggestion-list').innerHTML=items.map((item,index)=>`<article class="suggestion-card"><span class="suggestion-number">0${index+1}</span><p>${escapeHtml(item)}</p></article>`).join('');
  $('#suggestions-count').textContent=`${items.length} tips`;
}
function refreshNetwork() {
  const latency=24+Math.floor(Math.random()*24),loss=(Math.random()*.8).toFixed(1),down=(75+Math.random()*30).toFixed(1),up=(19+Math.random()*13).toFixed(1);
  $('#latency').textContent=latency;$('#packet-loss').textContent=loss;$('#download-speed').textContent=down;$('#upload-speed').textContent=up;
  showToast('Simulated network status refreshed.');
}
function refreshSignal() {
  const signal=-45-Math.floor(Math.random()*31),quality=Math.max(35,Math.min(97,Math.round((signal+100)*1.55)));
  $('#signal-db').textContent=signal;$('#signal-quality').textContent=`${quality}%`;$('#signal-progress').style.width=`${quality}%`;
  $('#signal-quality-label').textContent=quality>75?'Very good signal':quality>55?'Good signal':'Fair signal';
  const bars=$$('#network-signal-bars i');bars.forEach((bar,index)=>bar.style.background=index<Math.ceil(quality/20)?'#3ab38b':'#e5e9ed');
  showToast(`Simulated signal refreshed: ${signal} dBm.`);
}
function optimizeWifi() {
  const button=$('#optimize-wifi');button.disabled=true;button.innerHTML='<span class="button-spinner"></span> Analyzing demo signal...';
  window.setTimeout(()=>{const signal=-43-Math.floor(Math.random()*12),quality=82+Math.floor(Math.random()*14);$('#signal-db').textContent=signal;$('#signal-quality').textContent=`${quality}%`;$('#signal-progress').style.width=`${quality}%`;$('#signal-quality-label').textContent='Very good signal';$$('#network-signal-bars i').forEach(bar=>bar.style.background='#3ab38b');renderSuggestions([...suggestions].sort(()=>Math.random()-.5));button.disabled=false;button.innerHTML='<svg viewBox="0 0 24 24"><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3Z"/><path d="m19 14 .9 2.1L22 17l-2.1.9L19 20l-.9-2.1L16 17l2.1-.9L19 14Z"/></svg>Optimize Wi-Fi';showToast('Demo optimization complete. Router settings were not changed.');},1150);
}
function runSpeedTest() {
  const body='<div class="speed-test-state" id="speed-test-state"><div class="speed-test-gauge">···</div><p id="speed-test-message">Measuring simulated connection speed...</p></div><p class="dialog-note">This is a local simulation and does not send or receive network traffic.</p>';
  dialogFrame('Simulated speed test','Demo connection · no external network request',body,`<button class="button button-outline button-small" data-dialog-close>Close</button>`);
  window.setTimeout(()=>{const state=$('#speed-test-state');if(!state)return;state.classList.add('done');state.querySelector('.speed-test-gauge').textContent='✓';$('#speed-test-message').textContent='Simulated test complete';state.insertAdjacentHTML('beforeend',`<div class="speed-test-results"><span>DOWNLOAD<strong>${(75+Math.random()*30).toFixed(1)} Mbps</strong></span><span>UPLOAD<strong>${(19+Math.random()*13).toFixed(1)} Mbps</strong></span><span>LATENCY<strong>${24+Math.floor(Math.random()*24)} ms</strong></span></div>`);},1300);
}

function runGlobalSearch() {
  const query=$('#global-search').value.trim();if(!query)return;
  const lowered=query.toLowerCase();
  const customer=customers.find(item=>`${item.id} ${item.name}`.toLowerCase().includes(lowered));
  const ticket=tickets.find(item=>`${item.id} ${item.customerId} ${item.category}`.toLowerCase().includes(lowered));
  if(customer){switchSection('customers');$('#customer-search').value=query;renderCustomers();showToast(`Showing customer result for “${query}”.`);}
  else if(ticket){switchSection('tickets');$('#ticket-search').value=query;renderTickets();showToast(`Showing ticket result for “${query}”.`);}
  else {showToast(`No customer or ticket found for “${query}”.`,'warning');}
}

$('#login-form').addEventListener('submit',event=>{
  event.preventDefault();const username=$('#username').value.trim().toLowerCase(),password=$('#password').value;
  if(!username||!password){$('#login-error').textContent='Enter your username and password to continue.';return;}
  if(username!=='demo.employee'||password!=='Demo@123'){$('#login-error').textContent='Those details did not match. Use the demo credentials shown below.';return;}
  $('#login-error').textContent='';$('#login-screen').classList.add('is-hidden');$('#app-shell').classList.remove('is-hidden');renderOverview();renderCustomers();renderTickets();renderBilling();renderSuggestions();showToast('Signed in to the local TCL Enterprise demo.');
});
$('#password-toggle').addEventListener('click',event=>{const input=$('#password'),visible=input.type==='password';input.type=visible?'text':'password';event.currentTarget.textContent=visible?'Hide':'Show';event.currentTarget.setAttribute('aria-label',visible?'Hide password':'Show password');});
$('#logout-button').addEventListener('click',()=>{closeDialog();$('#app-shell').classList.add('is-hidden');$('#login-screen').classList.remove('is-hidden');$('#profile-menu').classList.add('is-hidden');$('#password').value='';$('#login-error').textContent='';showToast('You have signed out of the local demo.');});
$$('.nav-link[data-section]').forEach(link=>link.addEventListener('click',()=>switchSection(link.dataset.section)));
$$('[data-go-section]').forEach(button=>button.addEventListener('click',()=>switchSection(button.dataset.goSection)));
$$('[data-go-profile]').forEach(button=>button.addEventListener('click',()=>switchSection('profile')));
$('#mobile-menu').addEventListener('click',()=>{$('#sidebar').classList.add('mobile-open');$('#sidebar-backdrop').classList.add('visible');});
$('#sidebar-backdrop').addEventListener('click',()=>{$('#sidebar').classList.remove('mobile-open');$('#sidebar-backdrop').classList.remove('visible');});
$('#profile-menu-button').addEventListener('click',()=>{const menu=$('#profile-menu');menu.classList.toggle('is-hidden');$('#profile-menu-button').setAttribute('aria-expanded',String(!menu.classList.contains('is-hidden')));});
$('#notifications-button').addEventListener('click',()=>showToast('You are all caught up. 3 demo tickets need attention.','warning'));
$('#help-button').addEventListener('click',()=>showToast('For this prototype, service desk contact is simulated.','warning'));
$('#global-search').addEventListener('keydown',event=>{if(event.key==='Enter')runGlobalSearch();});
$('#global-search').addEventListener('search',runGlobalSearch);
$('#customer-search').addEventListener('input',renderCustomers);$('#customer-status-filter').addEventListener('change',renderCustomers);$('#customer-service-filter').addEventListener('change',renderCustomers);
$$('[data-sort]').forEach(button=>button.addEventListener('click',()=>{const key=button.dataset.sort;customerSort=customerSort.key===key?{key,direction:-customerSort.direction}:{key,direction:1};renderCustomers();}));
$('#customer-export').addEventListener('click',exportCustomers);$('#overview-export').addEventListener('click',exportCustomers);
$('#ticket-search').addEventListener('input',renderTickets);$('#ticket-status-filter').addEventListener('change',renderTickets);$('#ticket-category-filter').addEventListener('change',renderTickets);$('#create-ticket').addEventListener('click',createTicketDialog);
$('#billing-search').addEventListener('input',renderBilling);$('#billing-status-filter').addEventListener('change',renderBilling);
$('#refresh-network').addEventListener('click',refreshNetwork);$('#overview-network-refresh').addEventListener('click',refreshNetwork);$('#refresh-signal').addEventListener('click',refreshSignal);$('#optimize-wifi').addEventListener('click',optimizeWifi);$('#run-speed-test').addEventListener('click',runSpeedTest);
$('#connection-details').addEventListener('click',()=>dialogFrame('Connection details','Simulated service profile',`<div class="detail-grid"><div class="detail-item"><span>SERVICE PROFILE</span><strong>TCL Fiber Home 100</strong></div><div class="detail-item"><span>ROUTER REFERENCE</span><strong>DEMO-RTR-0084</strong></div><div class="detail-item"><span>WI-FI BAND</span><strong>Dual band · 2.4 / 5 GHz</strong></div><div class="detail-item"><span>CONNECTED DEVICES</span><strong>8 fictional devices</strong></div><div class="detail-item"><span>UPTIME</span><strong>12 days · simulated</strong></div><div class="detail-item"><span>NETWORK REGION</span><strong>Islamabad · demo region</strong></div></div><p class="dialog-note">No router or real network is accessed or modified by this prototype.</p>`,`<button class="button button-primary button-small" data-dialog-close>Done</button>`));
$('#edit-profile').addEventListener('click',editProfileDialog);
$('#app-dialog').addEventListener('click',event=>{if(event.target===$('#app-dialog'))closeDialog();});
document.addEventListener('click',event=>{
  const close=event.target.closest('[data-dialog-close]');if(close){closeDialog();return;}
  const view=event.target.closest('[data-customer-view]');if(view){showCustomerDetails(view.dataset.customerView);return;}
  const edit=event.target.closest('[data-customer-edit]');if(edit){editCustomer(edit.dataset.customerEdit);return;}
  const remove=event.target.closest('[data-customer-delete]');if(remove){deleteCustomer(remove.dataset.customerDelete);return;}
  const ticket=event.target.closest('[data-ticket-view]');if(ticket){ticketDetails(ticket.dataset.ticketView);return;}
  const ticketShortcut=event.target.closest('[data-ticket-id]');if(ticketShortcut){switchSection('tickets');ticketDetails(ticketShortcut.dataset.ticketId);return;}
  const billing=event.target.closest('[data-billing-view]');if(billing){billingDetails(billing.dataset.billingView);return;}
  const saveStatus=event.target.closest('[data-ticket-status]');if(saveStatus){const record=tickets.find(item=>item.id===saveStatus.dataset.ticketStatus);if(record){record.status=$('#ticket-detail-status').value;record.updates.push(`Oct 13 · Status changed to ${record.status} in demo`);closeDialog();renderTickets();showToast(`${record.id} status updated in demo.`);}return;}
  if(!event.target.closest('#profile-menu')&&!event.target.closest('#profile-menu-button')){$('#profile-menu').classList.add('is-hidden');$('#profile-menu-button').setAttribute('aria-expanded','false');}
});

renderOverview();