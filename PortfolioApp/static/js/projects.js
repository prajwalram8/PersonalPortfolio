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
              <div class="card h-100">
                <img src="${post.image_url}" class="card-img-top" alt="${post.name}">
                <div class="card-body">
                  <h5 class="card-title">${post.name}</h5>
                  <a href="/projects-detail/${post.id}" class="btn btn-primary">Read More</a>
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
