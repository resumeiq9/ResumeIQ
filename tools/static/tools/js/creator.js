// Dynamic Work Experience / Education blocks for the Resume Creator form.
document.addEventListener('DOMContentLoaded', () => {
  const expList = document.getElementById('experience-list');
  const eduList = document.getElementById('education-list');
  const projList = document.getElementById('project-list');

  function addExperience() {
    const wrap = document.createElement('div');
    wrap.className = 'exp-entry';
    wrap.innerHTML = `
      <div class="entry-title">Experience Entry</div>
      <div class="field-row">
        <div class="field">
          <label>Job Title</label>
          <input type="text" name="exp_title">
        </div>
        <div class="field">
          <label>Company</label>
          <input type="text" name="exp_company">
        </div>
      </div>
      <div class="field">
        <label>Duration</label>
        <input type="text" name="exp_duration" placeholder="Jan 2023 - Present">
      </div>
      <div class="field">
        <label>Key achievements (one per line)</label>
        <textarea name="exp_bullets" rows="3" placeholder="Increased conversion rate by 18%&#10;Led a team of 4 engineers"></textarea>
      </div>
      <button type="button" class="btn btn-outline remove-entry" style="width:100%;">Remove</button>
    `;
    wrap.querySelector('.remove-entry').addEventListener('click', () => wrap.remove());
    expList.appendChild(wrap);
  }

  function addEducation() {
    const wrap = document.createElement('div');
    wrap.className = 'edu-entry';
    wrap.innerHTML = `
      <div class="entry-title">Education Entry</div>
      <div class="field-row">
        <div class="field">
          <label>Degree</label>
          <input type="text" name="edu_degree">
        </div>
        <div class="field">
          <label>School</label>
          <input type="text" name="edu_school">
        </div>
      </div>
      <div class="field">
        <label>Year</label>
        <input type="text" name="edu_year" placeholder="2024">
      </div>
      <button type="button" class="btn btn-outline remove-entry" style="width:100%;">Remove</button>
    `;
    wrap.querySelector('.remove-entry').addEventListener('click', () => wrap.remove());
    eduList.appendChild(wrap);
  }

  function addProject() {
    const wrap = document.createElement('div');
    wrap.className = 'exp-entry';
    wrap.innerHTML = `
      <div class="entry-title">Project Entry</div>
      <div class="field">
        <label>Project Title</label>
        <input type="text" name="project_title">
      </div>
      <div class="field">
        <label>Tech Used (comma separated)</label>
        <input type="text" name="project_tech" placeholder="React, Django, PostgreSQL">
      </div>
      <div class="field">
        <label>Short Description</label>
        <textarea name="project_desc" rows="2" placeholder="What it does and your role in it."></textarea>
      </div>
      <button type="button" class="btn btn-outline remove-entry" style="width:100%;">Remove</button>
    `;
    wrap.querySelector('.remove-entry').addEventListener('click', () => wrap.remove());
    projList.appendChild(wrap);
  }

  document.getElementById('add-experience').addEventListener('click', addExperience);
  document.getElementById('add-education').addEventListener('click', addEducation);
  document.getElementById('add-project').addEventListener('click', addProject);

  // Start with one experience/education so the form doesn't look empty;
  // projects stay optional and start empty.
  addExperience();
  addEducation();

  // Show/hide the declaration "Place" field based on the checkbox.
  const declCheckbox = document.getElementById('include_declaration');
  const declPlaceField = document.getElementById('declaration-place-field');
  function syncDeclarationField() {
    if (declCheckbox && declPlaceField) {
      declPlaceField.style.display = declCheckbox.checked ? '' : 'none';
    }
  }
  if (declCheckbox) {
    declCheckbox.addEventListener('change', syncDeclarationField);
    syncDeclarationField();
  }
});
