// تابع برای دریافت محصولات از API
async function fetchProducts() {
    try {
        const response = await fetch('https://yourusername.pythonanywhere.com/api/products');
        const data = await response.json();
        if (data.success) {
            displayProducts(data.products);
        } else {
            document.getElementById('products').innerHTML = '<p>خطا در بارگذاری محصولات!</p>';
        }
    } catch (error) {
        console.error('Error fetching products:', error);
        document.getElementById('products').innerHTML = '<p>خطا در اتصال به سرور!</p>';
    }
}

// تابع برای نمایش محصولات
function displayProducts(products) {
    const productsDiv = document.getElementById('products');
    productsDiv.innerHTML = ''; // پاک کردن محتوای قبلی
    products.forEach(product => {
        const productDiv = document.createElement('div');
        productDiv.className = 'product';
        productDiv.innerHTML = `
            <h3>${product.text || 'بدون توضیح'}</h3>
            <p>دسته‌بندی: ${product.tags.join(', ')}</p>
            <button onclick="getProduct(${product.message_id})">دریافت محصول</button>
        `;
        productsDiv.appendChild(productDiv);
    });
}

// تابع برای خرید اشتراک
function buySubscription() {
    Telegram.WebApp.sendData(JSON.stringify({ action: 'buy_subscription' }));
}

// تابع برای دریافت محصول
async function getProduct(messageId) {
    // چک کردن وضعیت VIP
    const userId = Telegram.WebApp.initDataUnsafe.user?.id;
    if (!userId) {
        alert('لطفاً از تلگرام وارد شوید!');
        return;
    }

    try {
        const response = await fetch(`https://yourusername.pythonanywhere.com/api/is_vip?user_id=${userId}`);
        const data = await response.json();
        if (data.is_vip) {
            // ارسال درخواست برای دریافت محصول
            Telegram.WebApp.sendData(JSON.stringify({ action: 'get_product', message_id: messageId }));
        } else {
            alert('برای دریافت محصول، ابتدا اشتراک ویژه بخرید!');
        }
    } catch (error) {
        console.error('Error checking VIP status:', error);
        alert('خطا در بررسی وضعیت اشتراک!');
    }
}

// لود محصولات هنگام باز شدن مینی اپ
Telegram.WebApp.ready();
fetchProducts();