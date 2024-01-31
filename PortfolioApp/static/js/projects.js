function filterPosts(category) {
  $.ajax({
    url: `/filter-posts/${category}`, // Flask route to filter posts
    type: 'GET',
    success: function(data) {
      var postsContainer = $('#post-container');
      postsContainer.empty();
      
      if (data.posts.length === 0) {
        // If there are no posts, display the 'Coming Soon' message
        var comingSoonHtml = `
          <div class="col-12 d-flex justify-content-center align-items-center coming-soon-container">
            <div class="text-center">
              <h2>Posts Coming Soon</h2>
              <p>Explore other categories in this blog or check back later.</p>
            </div>
          </div>
        `;
        postsContainer.append(comingSoonHtml);
      } else {
        // Insert new posts into the container
        data.posts.forEach(post => {
          var postHtml = `
            <div class="col">
              <div class="card h-100 d-flex flex-column">
                <img src="https://prajwalramgowda.blr1.cdn.digitaloceanspaces.com/project_img.jpg" class="card-img-top" alt="${post.name}">
                <div class="card-body d-flex flex-column">
                  <h5 class="card-title card-content-title">${post.name}</h5>
                  <p class="card-text card-content-text"><small class="text-muted">${post.category_name}</small></p>
                  <a href="/blog-post/${post.id}" class="btn btn-secondary btn-custom-height">Read Post</a>
                </div>
                <div class="card-footer text-muted">
                  ${post.upload_date}
                </div>
              </div>
            </div>
          `;
          postsContainer.append(postHtml);
        });
      }
    },
    error: function(error) {
      console.error('Error fetching posts:', error);
    }
  });
}
